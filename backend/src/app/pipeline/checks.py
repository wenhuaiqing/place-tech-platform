"""Data checks: find the data-entry errors before they reach a report.

Each check reads the business data - never truth_defect - and records what
it found in check_result. Records a report must not count are quarantined,
and the v_* views leave them out, so every figure on screen is from data
that passed. The Data checks page lists every finding and which reports it
was kept out of.
"""

from __future__ import annotations

import duckdb

CHECKS = {
    "C01": ("Duplicate listing", "The same address listed by a second office within 30 days. The later listing is kept out of every count.", "Sales, Offices, Marketing"),
    "C02": ("Settlement before contract", "A settlement date earlier than the contract date. Kept out of settlement and commission figures until corrected.", "Sales, Overview"),
    "C03": ("Commission split not 100%", "The agents' shares of a sale do not add up. Kept out of agent commission; the office total still counts the sale.", "Sales (agents)"),
    "C04": ("Price far outside the appraisal", "A sale price more than three times the top of its appraisal: almost always a keying error. Kept out of price and commission figures.", "Sales, Overview, Offices"),
    "C05": ("Arrears after the tenancy ended", "An arrears entry dated after the tenancy's end. Kept out of arrears figures.", "Rentals, Overview"),
    "C06": ("Listing with no agent", "A listing nobody owns. Kept out of agent figures; the office still counts it.", "Sales (agents)"),
    "C07": ("Bond matching no tenancy", "A bond receipt whose tenancy does not exist. Kept out of bond compliance; someone must find whose money it is.", "Rentals (compliance)"),
}

SQL = {
    "C01": """SELECT 'listing', b.listing_id, b.office_code,
                     'Also listed by ' || a.office_code || ' as ' || a.listing_id || ' on ' || strftime(a.listed_on, '%d/%m/%Y')
              FROM listing a JOIN listing b ON a.address = b.address AND a.listing_id < b.listing_id
                   AND b.listed_on BETWEEN a.listed_on AND a.listed_on + INTERVAL 30 DAY AND a.office_code <> b.office_code""",
    "C02": """SELECT 'listing', listing_id, office_code,
                     'Contract ' || strftime(contract_on, '%d/%m/%Y') || ', settlement ' || strftime(settle_on, '%d/%m/%Y')
              FROM listing WHERE settle_on < contract_on""",
    "C03": """SELECT 'listing', s.listing_id, l.office_code, 'Shares add to ' || (sum(s.share_bp) / 100) || '%'
              FROM commission_split s JOIN listing l USING (listing_id) GROUP BY s.listing_id, l.office_code HAVING sum(s.share_bp) <> 10000""",
    "C04": """SELECT 'listing', l.listing_id, l.office_code,
                     'Price $' || format('{:,}', l.price_cents // 100) || ' against an appraisal of up to $' || format('{:,}', a.estimate_high_cents // 100)
              FROM listing l JOIN appraisal a USING (appraisal_id) WHERE l.price_cents > 3 * a.estimate_high_cents""",
    "C05": """SELECT 'tenancy', s.tenancy_id, t.office_code,
                     'Arrears of ' || s.days || ' days on ' || strftime(s.week_ending, '%d/%m/%Y') || '; tenancy ended ' || strftime(t.end_on, '%d/%m/%Y')
              FROM arrears_snapshot s JOIN tenancy t USING (tenancy_id) WHERE t.end_on IS NOT NULL AND s.week_ending > t.end_on""",
    "C06": """SELECT 'listing', listing_id, office_code, 'Listed ' || strftime(listed_on, '%d/%m/%Y') || ' with no agent'
              FROM listing WHERE agent_id IS NULL""",
    "C07": """SELECT 'bond', b.bond_id, b.office_code, 'Receipt for ' || b.tenancy_id || ', which does not exist'
              FROM bond b LEFT JOIN tenancy t USING (tenancy_id) WHERE t.tenancy_id IS NULL""",
}

# Which findings keep a record out of which views.
# C05 needs no quarantine row: the arrears view leaves out any entry dated after its tenancy ended.
QUARANTINE = {"C01": "listing", "C02": "listing", "C04": "listing", "C07": "bond"}


def run(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    found = {}
    for check_id, sql in SQL.items():
        rows = con.execute(sql).fetchall()
        con.executemany("INSERT INTO check_result VALUES (?, ?, ?, ?, ?)", [(check_id, *r) for r in rows])
        if check_id in QUARANTINE:
            con.executemany("INSERT INTO quarantine VALUES (?, ?, ?)", [(r[0], r[1], check_id) for r in rows])
        found[check_id] = len(rows)
    return found

