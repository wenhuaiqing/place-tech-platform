"""The reports. Every figure is a query over the v_* views, which already
leave out what the data checks quarantined. Year-on-year compares this
financial year to date with the same days a year earlier."""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from src.app.pipeline import acceptance, checks
from src.app.pipeline import reference as ref
from src.app.services import audit, catalogue, db, llm, sql_validator
from src.app.services.agents import runs
from src.app.services.auth import actor, require_write_token
from src.settings import REPO_ROOT, settings

router = APIRouter(prefix="/api", tags=["reports"])
STARTED = time.time()
EVAL_STATUS = REPO_ROOT / "evals" / "status.json"

FY = f"DATE '{ref.FY_START}' AND DATE '{ref.TODAY}'"
PY = f"DATE '{ref.PRIOR_FY_START}' AND DATE '{ref.PRIOR_TODAY}'"
TODAY = f"DATE '{ref.TODAY}'"


class _Where(str):
    """A SQL filter for one office, or none; w.on("s") qualifies it for an alias.
    Only a single letter A to Z ever reaches the SQL."""
    code: str | None = None

    def on(self, alias: str) -> str:
        return f"{alias}.office_code = '{self.code}'" if self.code else "TRUE"


def _office(office: str | None) -> _Where:
    if not office:
        return _Where("TRUE")
    code = office.strip().upper()
    if len(code) != 1 or not "A" <= code <= "Z":
        raise HTTPException(422, "Office is a letter from A to Z.")
    w = _Where(f"office_code = '{code}'")
    w.code = code
    return w


def one(sql: str) -> dict[str, Any]:
    rows = db.rows(sql)
    return rows[0] if rows else {}


def sales_kpis(where: str, period: str) -> dict:
    return one(f"""
        SELECT (SELECT count(*) FROM v_appraisals WHERE {where} AND appraised_on BETWEEN {period}) AS appraisals,
               (SELECT count(*) FROM v_listings WHERE {where} AND listed_on BETWEEN {period}) AS new_listings,
               count(*) AS sales, sum(commission) AS commission, median(price) AS median_price, median(days_on_market) AS median_dom,
               (SELECT round(count(*) FILTER (WHERE auction_result = 'sold') * 100.0 / nullif(count(*), 0), 1) FROM v_listings
                WHERE {where} AND auction_result IS NOT NULL AND listed_on BETWEEN {period}) AS clearance_pct
        FROM v_sales WHERE {where} AND contract_on BETWEEN {period}""")


def rentals_kpis(where: str) -> dict:
    return one(f"""
        WITH latest AS (SELECT max(week_ending) AS w FROM v_arrears)
        SELECT (SELECT count(*) FROM v_tenancies WHERE {where} AND current) AS managed,
               (SELECT sum(weekly_rent) FROM v_tenancies WHERE {where} AND current) AS weekly_rent_roll,
               (SELECT count(*) FROM v_arrears, latest WHERE {where} AND week_ending = latest.w) AS in_arrears,
               (SELECT count(*) FROM v_arrears, latest WHERE {where} AND week_ending = latest.w AND days > {ref.ARREARS_WATCH_DAYS}) AS over_watch,
               (SELECT sum(amount) FROM v_arrears, latest WHERE {where} AND week_ending = latest.w) AS arrears_amount,
               (SELECT w FROM latest) AS arrears_week,
               (SELECT count(*) FROM v_tenancies WHERE {where} AND current AND lease_end BETWEEN {TODAY} AND {TODAY} + INTERVAL 60 DAY) AS renewals_60d,
               (SELECT count(*) FROM v_maintenance WHERE {where} AND completed_on IS NULL) AS open_jobs,
               (SELECT count(*) FROM v_maintenance WHERE {where} AND completed_on IS NULL AND priority = 'urgent' AND days_open > 3) AS urgent_late,
               (SELECT round(count(*) FILTER (WHERE days_to_lodge > {ref.BOND_LODGE_DAYS}) * 100.0 / nullif(count(*), 0), 1)
                FROM v_bonds WHERE {where} AND received_on BETWEEN {FY} AND lodged_on IS NOT NULL) AS bonds_late_pct,
               (SELECT round(avg(vacant_days), 1) FROM v_vacancies WHERE {where} AND relet_on BETWEEN {FY}) AS avg_vacant_days""")


@router.get("/meta")
def meta() -> dict:
    return {
        "version": settings.git_sha or "dev", "uptime_seconds": int(time.time() - STARTED), "synthetic_data": True,
        "today": ref.TODAY.isoformat(), "fy_start": ref.FY_START.isoformat(), "prior_fy_start": ref.PRIOR_FY_START.isoformat(),
        "prior_today": ref.PRIOR_TODAY.isoformat(),
        "llm_configured": llm.configured(), "llm_model": settings.llm_chat_model if llm.configured() else None,
        "offices": db.rows("SELECT office_code, office, region FROM v_offices ORDER BY 1"),
        "build_seconds": db.kv("build_seconds"),
    }


@router.get("/overview")
def overview() -> dict:
    return {
        "sales": {"this_year": sales_kpis("TRUE", FY), "last_year": sales_kpis("TRUE", PY)},
        "rentals": rentals_kpis("TRUE"),
        "monthly": db.rows("""SELECT strftime(date_trunc('month', contract_on), '%Y-%m') AS month, count(*) AS sales, sum(commission) AS commission
                              FROM v_sales WHERE contract_on >= DATE '2025-07-01' GROUP BY 1 ORDER BY 1"""),
        "offices": offices()["offices"],
        "checks": db.scalar("SELECT count(*) FROM check_result"),
    }


@router.get("/sales")
def sales(office: str | None = None) -> dict:
    w = _office(office)
    return {
        "this_year": sales_kpis(w, FY), "last_year": sales_kpis(w, PY),
        "funnel": one(f"""SELECT (SELECT count(*) FROM v_appraisals WHERE {w} AND appraised_on BETWEEN {FY}) AS appraisals,
                                 (SELECT count(*) FROM v_appraisals WHERE {w} AND appraised_on BETWEEN {FY} AND became_listing) AS became_listings,
                                 (SELECT count(*) FROM v_listings WHERE {w} AND listed_on BETWEEN {FY}) AS listed,
                                 (SELECT count(*) FROM v_listings WHERE {w} AND listed_on BETWEEN {FY} AND contract_on IS NOT NULL) AS sold,
                                 (SELECT count(*) FROM v_listings WHERE {w} AND listed_on BETWEEN {FY} AND status = 'withdrawn') AS withdrawn,
                                 (SELECT count(*) FROM v_listings WHERE {w} AND status = 'active') AS on_market"""),
        "monthly": db.rows(f"""SELECT m AS month,
                                      (SELECT count(*) FROM v_listings WHERE {w} AND strftime(listed_on, '%Y-%m') = m) AS listings,
                                      (SELECT count(*) FROM v_sales WHERE {w} AND strftime(contract_on, '%Y-%m') = m) AS sales
                               FROM (SELECT DISTINCT strftime(listed_on, '%Y-%m') AS m FROM v_listings WHERE listed_on >= DATE '2025-07-01') ORDER BY 1"""),
        "by_method": db.rows(f"""SELECT method, count(*) AS sales, median(days_on_market) AS median_dom, median(price) AS median_price
                                 FROM v_sales WHERE {w} AND contract_on BETWEEN {FY} GROUP BY 1 ORDER BY 1"""),
        "pipeline": one(f"""SELECT count(*) AS pending, sum(commission) AS commission,
                                   count(*) FILTER (WHERE settle_on <= {TODAY} + INTERVAL 30 DAY) AS next_30_days
                            FROM v_sales WHERE {w} AND settle_on > {TODAY}"""),
        "settling": db.rows(f"""SELECT listing_id, office_code, address, contract_on, settle_on, price, commission FROM v_sales
                                WHERE {w} AND settle_on > {TODAY} ORDER BY settle_on, listing_id LIMIT 25"""),
        "agents": db.rows(f"""SELECT s.staff_id, s.name, s.office_code, coalesce(c.commission, 0) AS commission, coalesce(c.sales, 0) AS sales,
                                     coalesce(a.appraisals, 0) AS appraisals, coalesce(a.listed, 0) AS listed
                              FROM v_staff s
                              LEFT JOIN (SELECT agent_id, sum(commission_share) AS commission, count(*) AS sales FROM v_commission_by_agent
                                         WHERE contract_on BETWEEN {FY} GROUP BY 1) c ON c.agent_id = s.staff_id
                              LEFT JOIN (SELECT agent_id, count(*) AS appraisals, count(*) FILTER (WHERE became_listing) AS listed FROM v_appraisals
                                         WHERE appraised_on BETWEEN {FY} GROUP BY 1) a ON a.agent_id = s.staff_id
                              WHERE s.role = 'sales' AND {w.on('s')} ORDER BY commission DESC, s.staff_id LIMIT 40"""),
    }


@router.get("/rentals")
def rentals(office: str | None = None) -> dict:
    w = _office(office)
    return {
        "kpis": rentals_kpis(w),
        "arrears_trend": db.rows(f"""SELECT a.week_ending, count(*) AS in_arrears, count(*) FILTER (WHERE a.days > {ref.ARREARS_WATCH_DAYS}) AS over_watch,
                                            round(count(*) * 100.0 / (SELECT count(*) FROM v_tenancies t WHERE {w.on('t')} AND t.start_on <= a.week_ending
                                                  AND coalesce(t.end_on, DATE '2999-01-01') >= a.week_ending), 2) AS pct
                                     FROM v_arrears a WHERE {w.on('a')} AND a.week_ending >= {TODAY} - INTERVAL 182 DAY GROUP BY 1 ORDER BY 1"""),
        "watch": db.rows(f"""SELECT a.tenancy_id, a.office_code, s.name AS property_manager, a.days, a.amount, t.weekly_rent
                             FROM v_arrears a JOIN v_tenancies t ON t.tenancy_id = a.tenancy_id JOIN v_staff s ON s.staff_id = a.pm_id
                             WHERE {w.on('a')} AND a.week_ending = (SELECT max(week_ending) FROM v_arrears) AND a.days > {ref.ARREARS_WATCH_DAYS}
                             ORDER BY a.days DESC, a.tenancy_id LIMIT 40"""),
        "renewals": db.rows(f"""SELECT strftime(date_trunc('week', lease_end), '%Y-%m-%d') AS week, count(*) AS leases
                                FROM v_tenancies WHERE {w} AND current AND lease_end BETWEEN {TODAY} AND {TODAY} + INTERVAL 60 DAY GROUP BY 1 ORDER BY 1"""),
        "maintenance": db.rows(f"""SELECT category, count(*) FILTER (WHERE completed_on IS NULL) AS open, count(*) FILTER (WHERE reported_on BETWEEN {FY}) AS reported_fytd,
                                          round(median(days_open) FILTER (WHERE completed_on IS NOT NULL AND reported_on BETWEEN {FY}), 1) AS median_days_to_complete,
                                          sum(cost) FILTER (WHERE reported_on BETWEEN {FY}) AS cost_fytd
                                   FROM v_maintenance WHERE {w} GROUP BY 1 ORDER BY 2 DESC, 1"""),
        "urgent_late": db.rows(f"""SELECT job_id, office_code, category, reported_on, days_open FROM v_maintenance
                                   WHERE {w} AND priority = 'urgent' AND completed_on IS NULL AND days_open > 3 ORDER BY days_open DESC"""),
        "bonds_late": db.rows(f"""SELECT bond_id, tenancy_id, office_code, received_on, lodged_on, days_to_lodge, amount FROM v_bonds
                                  WHERE {w} AND received_on BETWEEN {FY} AND (days_to_lodge > {ref.BOND_LODGE_DAYS}
                                        OR (lodged_on IS NULL AND received_on < {TODAY} - INTERVAL {ref.BOND_LODGE_DAYS} DAY))
                                  ORDER BY received_on DESC LIMIT 30"""),
    }


@router.get("/offices")
def offices() -> dict:
    rows = db.rows(f"""
        WITH staff_n AS (SELECT office_code, count(*) FILTER (WHERE role = 'sales') AS agents,
                                count(*) FILTER (WHERE role = 'property') AS property_managers FROM v_staff GROUP BY 1),
             sales_ty AS (SELECT office_code, count(*) AS sales, sum(commission) AS commission, median(days_on_market) AS median_dom
                          FROM v_sales WHERE contract_on BETWEEN {FY} GROUP BY 1),
             sales_py AS (SELECT office_code, sum(commission) AS commission_last_year FROM v_sales WHERE contract_on BETWEEN {PY} GROUP BY 1),
             managed AS (SELECT office_code, count(*) AS managed FROM v_tenancies WHERE current GROUP BY 1),
             arrears AS (SELECT office_code, count(*) AS in_arrears, count(*) FILTER (WHERE days > {ref.ARREARS_WATCH_DAYS}) AS over_watch
                         FROM v_arrears WHERE week_ending = (SELECT max(week_ending) FROM v_arrears) GROUP BY 1),
             issues AS (SELECT office_code, count(*) AS data_issues FROM check_result GROUP BY 1)
        SELECT o.office_code, o.office, o.region, s.agents, s.property_managers, coalesce(ty.sales, 0) AS sales, ty.commission,
               py.commission_last_year, ty.median_dom, m.managed,
               round(coalesce(a.in_arrears, 0) * 100.0 / nullif(m.managed, 0), 1) AS arrears_pct, coalesce(a.over_watch, 0) AS over_watch,
               coalesce(i.data_issues, 0) AS data_issues
        FROM v_offices o LEFT JOIN staff_n s ON s.office_code = o.office_code LEFT JOIN sales_ty ty ON ty.office_code = o.office_code
             LEFT JOIN sales_py py ON py.office_code = o.office_code LEFT JOIN managed m ON m.office_code = o.office_code
             LEFT JOIN arrears a ON a.office_code = o.office_code LEFT JOIN issues i ON i.office_code = o.office_code
        ORDER BY o.office_code""")
    return {"offices": rows}


@router.get("/marketing")
def marketing(office: str | None = None) -> dict:
    w = _office(office)
    return {
        "totals": one(f"""SELECT count(*) AS listings, sum(budget) AS budget, sum(spend) AS spend, count(*) FILTER (WHERE spend > budget) AS over_budget,
                                 sum(enquiries) AS enquiries, round(sum(spend) / nullif(sum(enquiries), 0), 2) AS cost_per_enquiry
                          FROM v_marketing m JOIN v_listings l USING (listing_id) WHERE {w.on('m')} AND l.listed_on BETWEEN {FY}"""),
        "channels": db.rows(f"""SELECT e.channel, sum(e.enquiries) AS enquiries FROM v_enquiries e JOIN v_listings l USING (listing_id)
                                WHERE {w.on('e')} AND l.listed_on BETWEEN {FY} GROUP BY 1 ORDER BY 2 DESC"""),
        "by_office": db.rows(f"""SELECT m.office_code, count(*) AS listings, sum(m.spend) AS spend, sum(m.budget) AS budget,
                                        round(sum(m.spend) / nullif(sum(m.enquiries), 0), 2) AS cost_per_enquiry,
                                        count(*) FILTER (WHERE m.spend > m.budget) AS over_budget
                                 FROM v_marketing m JOIN v_listings l USING (listing_id) WHERE l.listed_on BETWEEN {FY} GROUP BY 1 ORDER BY 1"""),
        "most_over": db.rows(f"""SELECT m.listing_id, m.office_code, l.address, m.budget, m.spend, m.spend - m.budget AS over_by
                                 FROM v_marketing m JOIN v_listings l USING (listing_id)
                                 WHERE {w.on('m')} AND l.listed_on BETWEEN {FY} AND m.spend > m.budget ORDER BY over_by DESC LIMIT 15"""),
    }


@router.get("/checks")
def data_checks() -> dict:
    counts = dict(db.query("SELECT check_id, count(*) FROM check_result GROUP BY 1").values.tolist())
    return {
        "checks": [{"check_id": k, "name": v[0], "what": v[1], "reports": v[2], "found": counts.get(k, 0)} for k, v in checks.CHECKS.items()],
        "findings": db.rows("SELECT check_id, record_kind, record_id, office_code, detail FROM check_result ORDER BY check_id, record_id"),
        "acceptance": [name for name, _ in acceptance.CHECKS],
    }


@router.get("/ask")
def ask() -> dict:
    status = json.loads(EVAL_STATUS.read_text(encoding="utf-8")) if EVAL_STATUS.exists() else None
    return {
        "configured": llm.configured(), "model": settings.llm_chat_model if llm.configured() else None,
        "views": catalogue.schema(), "rules": catalogue.RULES,
        "known": [{"question": q, "sql": sql} for q, sql, _ in catalogue.KNOWN],
        "gate": {"allowed_views": sorted(sql_validator.ALLOWED_TABLES), "forbidden_keywords": sorted(sql_validator.FORBIDDEN_KEYWORDS),
                 "forbidden_functions": sorted(sql_validator.FORBIDDEN_FUNCTIONS),
                 "default_limit": sql_validator.DEFAULT_LIMIT, "max_limit": sql_validator.MAX_LIMIT},
        "eval": status, "runs": runs.summary(),
    }


@router.post("/ask/gate")
def gate(body: dict) -> dict:
    """Put any SQL to the gate and see what it says. Runs nothing."""
    sql = str(body.get("sql", ""))[:2000]
    outcome = sql_validator.validate(sql)
    return {"ok": outcome.ok, "errors": outcome.errors, "sql": outcome.sql if outcome.ok else None, "tables": outcome.tables_referenced}


@router.post("/reset", dependencies=[Depends(require_write_token)])
def reset(request: Request) -> dict:
    """Back to the built state: clears the assistant's run log."""
    db.reset_to_build()
    with db.writing() as cur:
        audit.record(cur, actor(request), "platform", "demo", "reset to built state")
    return {"reset": True}
