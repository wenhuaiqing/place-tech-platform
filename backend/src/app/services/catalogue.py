"""What the data agent is told about the data: every view it may read, what
each means, and the business rules a new analyst would have to be told.

It is also the Ask page's data dictionary and the source of the questions
answered without a model - one description of the data, used by the prompt,
the documentation and the fallback alike.
"""

from __future__ import annotations

from src.app.pipeline import reference as ref
from src.app.services import db
from src.app.services.sql_validator import ALLOWED_TABLES

VIEWS: dict[str, str] = {
    "v_offices": "The 26 offices: office_code (A to Z), office name and region.",
    "v_staff": "People: staff_id, name, office_code, role ('sales' agents or 'property' managers).",
    "v_appraisals": "Every appraisal: who did it, when, the estimate range in dollars, and whether it became a listing.",
    "v_listings": "Every listing: method ('auction' or 'private treaty'), status ('active', 'under contract', 'settled', 'withdrawn'), "
                  "auction_result ('sold' or 'passed in'), contract_on, settle_on, price and commission in dollars, days_on_market.",
    "v_sales": "Listings that went under contract (contract_on is set). Settled when settle_on <= today; otherwise pending settlement.",
    "v_commission_by_agent": "Each agent's share of each sale's commission, in dollars.",
    "v_tenancies": "Every tenancy: property, office, property manager (pm_id), weekly_rent in dollars, start_on, lease_end, end_on. "
                   "current is true for tenancies still running. renewal marks a tenancy that renewed the previous one.",
    "v_arrears": "Weekly arrears: one row per tenancy in arrears at week_ending, with days in arrears and amount in dollars. "
                 "A tenancy not in this view that week was paid up.",
    "v_maintenance": "Maintenance jobs: category, priority ('urgent' or 'routine'), reported_on, completed_on (empty while open), cost, days_open.",
    "v_bonds": "Bonds: received_on, lodged_on (empty if not yet lodged), days_to_lodge.",
    "v_marketing": "Vendor-paid advertising per listing: budget, spend, and total enquiries, in dollars.",
    "v_enquiries": "Enquiries per listing by channel.",
}

RULES = [
    f"Today is {ref.TODAY.isoformat()}. The financial year runs 1 July to 30 June; this financial year to date is "
    f"{ref.FY_START.isoformat()} to today, and the same days last year are {ref.PRIOR_FY_START.isoformat()} to {ref.PRIOR_TODAY.isoformat()}.",
    "A sale is counted on contract_on (when it went under contract). Settled sales are those with settle_on <= today.",
    "Commission is the agency's gross commission in dollars. Agents' shares are in v_commission_by_agent.",
    "Auction clearance rate = auctions with auction_result 'sold' / all auctions with a result.",
    "Current tenancies: v_tenancies where current. The rent roll is their count and sum(weekly_rent).",
    f"Arrears: for 'now' use the latest week_ending in v_arrears. The watch list is more than {ref.ARREARS_WATCH_DAYS} days.",
    f"A bond is lodged on time when days_to_lodge <= {ref.BOND_LODGE_DAYS}.",
    "Records the data checks found wrong are already left out of every view.",
    "Join with ON (a.x = b.x), never USING: the query checker cannot read USING joins.",
]

FY = f"DATE '{ref.FY_START}' AND DATE '{ref.TODAY}'"

# Questions with a known-good query. They seed the page, and they are what
# answers when no model is configured.
KNOWN = [
    ("How many sales settled this financial year, and for how much commission?",
     f"SELECT count(*) AS settled_sales, sum(price) AS total_price, sum(commission) AS commission FROM v_sales WHERE settle_on BETWEEN {FY}",
     ["settled", "settle", "sales", "commission", "year"]),
    ("Which offices have the most tenancies more than 14 days in arrears?",
     "SELECT a.office_code, o.office, count(*) AS over_14_days, sum(a.amount) AS amount FROM v_arrears a JOIN v_offices o ON o.office_code = a.office_code "
     "WHERE a.week_ending = (SELECT max(week_ending) FROM v_arrears) AND a.days > 14 GROUP BY 1, 2 ORDER BY 3 DESC, 1",
     ["arrears", "14", "days", "offices", "tenancies", "overdue"]),
    ("What is the auction clearance rate by region this financial year?",
     f"SELECT o.region, count(*) AS auctions, round(count(*) FILTER (WHERE auction_result = 'sold') * 100.0 / count(*), 1) AS clearance_pct "
     f"FROM v_listings l JOIN v_offices o ON o.office_code = l.office_code WHERE l.auction_result IS NOT NULL AND l.listed_on BETWEEN {FY} GROUP BY 1 ORDER BY 1",
     ["auction", "clearance", "region", "rate"]),
    ("Who are the top ten agents by commission this financial year?",
     f"SELECT s.name, s.office_code, sum(c.commission_share) AS commission, count(*) AS sales FROM v_commission_by_agent c JOIN v_staff s ON s.staff_id = c.agent_id "
     f"WHERE c.contract_on BETWEEN {FY} GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10",
     ["top", "agents", "agent", "commission", "best"]),
    ("What is the median days on market by method this year and last?",
     f"SELECT method, median(days_on_market) FILTER (WHERE contract_on BETWEEN {FY}) AS this_year, "
     f"median(days_on_market) FILTER (WHERE contract_on BETWEEN DATE '{ref.PRIOR_FY_START}' AND DATE '{ref.PRIOR_TODAY}') AS last_year FROM v_sales GROUP BY 1 ORDER BY 1",
     ["days", "market", "median", "method"]),
    ("How many leases end in the next 60 days, by office?",
     f"SELECT office_code, count(*) AS leases_ending FROM v_tenancies WHERE current AND lease_end BETWEEN DATE '{ref.TODAY}' AND DATE '{ref.TODAY}' + INTERVAL 60 DAY GROUP BY 1 ORDER BY 2 DESC",
     ["leases", "lease", "renewals", "ending", "expire", "60"]),
    ("Which urgent maintenance jobs have been open more than three days?",
     "SELECT job_id, office_code, category, reported_on, days_open FROM v_maintenance WHERE priority = 'urgent' AND completed_on IS NULL AND days_open > 3 ORDER BY days_open DESC",
     ["urgent", "maintenance", "open", "jobs", "repairs"]),
    ("Which offices spent most over their vendors' marketing budgets?",
     "SELECT office_code, sum(spend - budget) FILTER (WHERE spend > budget) AS over_budget, count(*) FILTER (WHERE spend > budget) AS listings_over "
     "FROM v_marketing GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
     ["marketing", "budget", "over", "spend", "vendor"]),
    ("How many bonds were lodged late this financial year?",
     f"SELECT count(*) FILTER (WHERE days_to_lodge > {ref.BOND_LODGE_DAYS}) AS late, count(*) AS lodged FROM v_bonds WHERE received_on BETWEEN {FY}",
     ["bonds", "bond", "lodged", "late", "lodgement"]),
]


def schema() -> list[dict]:
    cols = db.rows("""SELECT table_name, column_name, data_type FROM information_schema.columns
                      WHERE table_schema = 'main' ORDER BY table_name, ordinal_position""")
    out = []
    for view in VIEWS:
        if view not in ALLOWED_TABLES:
            continue
        out.append({"view": view, "description": VIEWS[view],
                    "columns": [{"name": c["column_name"], "type": c["data_type"]} for c in cols if c["table_name"] == view]})
    return out


def prompt_block() -> str:
    parts = []
    for v in schema():
        columns = ", ".join(f"{c['name']} {c['type']}" for c in v["columns"])
        parts.append(f"- {v['view']}: {v['description']}\n    columns: {columns}")
    return "\n".join(parts)


def best_known(question: str) -> tuple[str, str] | None:
    """The catalogue question closest to this one, by shared keywords. None if nothing is close."""
    words = set("".join(ch.lower() if ch.isalnum() else " " for ch in question).split())
    scored = [(sum(1 for k in keys if any(w.startswith(k) for w in words)), q, sql) for q, sql, keys in KNOWN]
    score, q, sql = max(scored)
    return (q, sql) if score >= 2 else None
