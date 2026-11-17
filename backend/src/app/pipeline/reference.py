"""Everything the synthetic agency is made of, declared once.

A residential agency with 26 offices (the number is from the advertisement;
everything else is invented): sales agents who appraise, list and sell, and
property managers who look after rentals. Offices are lettered, suburbs are
numbered, people have invented names - nothing here describes a real Place
office, person, property or result.

The `SEEDED` counts are the data-entry errors the generator puts in. The
pipeline never reads them: the data checks find each one from the data, and
the tests compare what was found with what was seeded.
"""

from __future__ import annotations

from datetime import date

SEED = 20261118
TODAY = date(2026, 11, 16)
# Six months before the prior financial year, so last year is steady-state, not ramping up.
HISTORY_START = date(2025, 1, 1)
# Financial year to date, and the same days a year earlier.
FY_START = date(2026, 7, 1)
PRIOR_FY_START = date(2025, 7, 1)
PRIOR_TODAY = date(2025, 11, 16)

REGIONS = ["North", "South", "East", "West", "Bayside", "Central"]
OFFICES = [(chr(65 + i), f"Office {chr(65 + i)}", REGIONS[min(i // 5, 5)]) for i in range(26)]

FIRST = ["Jordan", "Sam", "Alex", "Riley", "Casey", "Morgan", "Taylor", "Jamie", "Quinn", "Avery", "Harper", "Reese",
         "Charlie", "Skyler", "Rowan", "Emerson", "Finley", "Hayden", "Kendall", "Parker", "Sasha", "Drew", "Logan", "Blake"]
LAST = "ABCDEFGHJKLMNPRSTVW"

STREETS = ["Banksia St", "Wattle Rd", "Jacaranda Ave", "Fig Tree Pde", "Poinciana Cres", "Grevillea Ct", "Bottlebrush Dr",
           "Lilly Pilly Way", "Tallowwood St", "Ironbark Rd", "Paperbark Lane", "Brush Box Tce"]

# ---- Assumptions (labelled on screen wherever they are used) -----------------
# Commission is a percentage of the price agreed with each vendor; the range is
# an assumption for the synthetic data, in basis points.
COMMISSION_BP = (200, 275)
# Queensland bonds are lodged with the Residential Tenancies Authority; the
# report counts a lodgement as on time within 10 days of receipt. Check the
# current rule before relying on it.
BOND_LODGE_DAYS = 10
# A tenancy counts as in arrears from one day overdue; the watch list starts at 14.
ARREARS_WATCH_DAYS = 14

CHANNELS = ["Portal 1", "Portal 2", "Social", "Signboard", "Database"]
MAINTENANCE = ["Plumbing", "Electrical", "Appliance", "Locks and keys", "Garden", "General repairs", "Pest", "Roof and gutters"]

# ---- Seeded data-entry errors -----------------------------------------------------
SEEDED = {
    "duplicate_listing": 6,        # the same property listed by a second office within 30 days
    "settlement_before_contract": 5,
    "commission_split_not_100": 7,  # the agents' shares of a sale do not add to 100%
    "price_extra_digit": 4,         # a sale price keyed with an extra zero
    "arrears_after_vacate": 5,      # arrears still showing for a tenancy that has ended
    "listing_without_agent": 3,
    "bond_without_tenancy": 4,      # a bond receipt that matches no tenancy
}
