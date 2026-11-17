"""The reports' figures, cross-checked against the raw tables by a second route."""

from __future__ import annotations

from src.app.pipeline import reference as ref


def test_overview_sales_agree_with_the_raw_listings(client, built):
    ty = client.get("/api/overview").json()["sales"]["this_year"]
    raw = built.execute(f"""SELECT count(*) FROM listing WHERE contract_on BETWEEN DATE '{ref.FY_START}' AND DATE '{ref.TODAY}'
                            AND listing_id NOT IN (SELECT record_id FROM quarantine)""").fetchone()[0]
    assert ty["sales"] == raw


def test_commission_is_price_times_rate(built):
    bad = built.execute("SELECT count(*) FROM v_sales WHERE commission <> floor(price * commission_bp / 10000)").fetchone()[0]
    assert bad == 0


def test_office_figures_add_up_to_the_group(client):
    offices = client.get("/api/offices").json()["offices"]
    group = client.get("/api/overview").json()
    assert sum(o["sales"] for o in offices) == group["sales"]["this_year"]["sales"]
    assert sum(o["managed"] for o in offices) == group["rentals"]["managed"]


def test_one_office_is_a_subset(client):
    a = client.get("/api/sales?office=A").json()["this_year"]["sales"]
    total = client.get("/api/sales").json()["this_year"]["sales"]
    assert 0 < a < total


def test_bad_office_is_refused(client):
    assert client.get("/api/sales?office=A' OR 1=1 --").status_code == 422
    assert client.get("/api/rentals?office=ZZ").status_code == 422


def test_last_year_is_steady_state_not_a_ramp(client):
    s = client.get("/api/overview").json()["sales"]
    assert 0.8 < s["this_year"]["sales"] / s["last_year"]["sales"] < 1.25


def test_arrears_watch_list_is_over_the_threshold(client):
    watch = client.get("/api/rentals").json()["watch"]
    assert watch and all(w["days"] > ref.ARREARS_WATCH_DAYS for w in watch)


def test_no_tenant_details_anywhere(built):
    cols = {r[0] for r in built.execute("SELECT column_name FROM information_schema.columns").fetchall()}
    assert not any(c for c in cols if any(p in c for p in ("phone", "email", "tenant_name", "dob")))


def test_reads_are_open_and_reset_needs_the_token(client):
    assert client.get("/api/overview").status_code == 200
    assert client.post("/api/reset").status_code == 401
    assert client.post("/api/reset", headers={"X-Write-Token": "test-token"}).status_code == 200
