"""What must hold, or there is no build. Each check reads the built data."""

from __future__ import annotations

import duckdb

from src.app.pipeline import reference as ref


def _q(con, sql):
    return con.execute(sql).fetchone()[0]


def _every_error_found(con):
    found = _q(con, "SELECT count(*) FROM check_result")
    return found >= sum(ref.SEEDED.values()), f"{found} findings for {sum(ref.SEEDED.values())} seeded errors"


def _no_quarantined_in_reports(con):
    n = _q(con, "SELECT count(*) FROM v_listings WHERE listing_id IN (SELECT record_id FROM quarantine)")
    return n == 0, f"{n} quarantined listings still in v_listings"


def _no_arrears_after_end(con):
    n = _q(con, "SELECT count(*) FROM v_arrears a JOIN tenancy t USING (tenancy_id) WHERE t.end_on IS NOT NULL AND a.week_ending > t.end_on")
    return n == 0, f"{n} arrears entries after a tenancy ended"


def _splits_add_up(con):
    n = _q(con, "SELECT count(*) FROM (SELECT listing_id FROM commission_split WHERE listing_id IN (SELECT listing_id FROM v_commission_by_agent) GROUP BY 1 HAVING sum(share_bp) <> 10000)")
    return n == 0, f"{n} sales in agent commission whose shares do not add to 100%"


def _commission_reconciles(con):
    office = _q(con, "SELECT sum(commission) FROM v_sales WHERE listing_id NOT IN (SELECT record_id FROM check_result WHERE check_id IN ('C03', 'C06'))")
    agents = _q(con, "SELECT sum(commission_share) FROM v_commission_by_agent")
    return abs(office - agents) <= _q(con, "SELECT count(*) FROM v_commission_by_agent"), f"office ${office:,} against agents ${agents:,} (rounding per share)"


def _one_current_tenancy_per_property(con):
    n = _q(con, "SELECT count(*) FROM (SELECT property_id FROM tenancy WHERE end_on IS NULL GROUP BY 1 HAVING count(*) > 1)")
    return n == 0, f"{n} properties with two current tenancies"


def _nothing_in_the_future(con):
    n = _q(con, f"SELECT count(*) FROM listing WHERE listed_on > DATE '{ref.TODAY}' OR contract_on > DATE '{ref.TODAY}'")
    return n == 0, f"{n} listings or contracts dated after today"


CHECKS = [
    ("Every seeded data-entry error is found by a check", _every_error_found),
    ("No quarantined record reaches a report", _no_quarantined_in_reports),
    ("No arrears are counted after a tenancy ended", _no_arrears_after_end),
    ("Agent commission only counts sales whose shares add to 100%", _splits_add_up),
    ("Agent commission adds up to the office total", _commission_reconciles),
    ("A property has at most one current tenancy", _one_current_tenancy_per_property),
    ("Nothing is listed or contracted after today", _nothing_in_the_future),
]


def run(con: duckdb.DuckDBPyConnection) -> list[tuple[str, bool, str]]:
    return [(name, *fn(con)) for name, fn in CHECKS]
