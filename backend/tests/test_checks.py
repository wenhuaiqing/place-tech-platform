"""Every seeded data-entry error is found from the data - the checks never
read truth_defect - and nothing else is."""

from __future__ import annotations

import pytest

from src.app.pipeline import reference as ref

CHECK_FOR = {"duplicate_listing": "C01", "settlement_before_contract": "C02", "commission_split_not_100": "C03",
             "price_extra_digit": "C04", "arrears_after_vacate": "C05", "listing_without_agent": "C06", "bond_without_tenancy": "C07"}


@pytest.mark.parametrize("defect", sorted(ref.SEEDED))
def test_each_check_finds_exactly_what_was_seeded(built, defect):
    seeded = {r[0] for r in built.execute("SELECT record_id FROM truth_defect WHERE defect = ?", [defect]).fetchall()}
    found = {r[0] for r in built.execute("SELECT record_id FROM check_result WHERE check_id = ?", [CHECK_FOR[defect]]).fetchall()}
    assert len(seeded) == ref.SEEDED[defect]
    assert found == seeded


def test_quarantined_listings_reach_no_report(built):
    for view in ("v_listings", "v_sales", "v_marketing", "v_enquiries"):
        n = built.execute(f"SELECT count(*) FROM {view} WHERE listing_id IN (SELECT record_id FROM quarantine)").fetchone()[0]
        assert n == 0, view


def test_the_checks_do_not_read_the_truth_table():
    from src.app.pipeline import checks
    assert not any("truth_defect" in sql for sql in checks.SQL.values())


def test_the_agent_cannot_reach_the_truth_table():
    from src.app.services import sql_validator
    assert not sql_validator.validate("SELECT * FROM truth_defect").ok
