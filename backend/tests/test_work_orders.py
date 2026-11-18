"""The work orders' rules, each refused on the server and audit-logged."""

from __future__ import annotations

from src.app.pipeline import reference as ref

AV, JO, HEAD = "Property manager - Avery", "Property manager - Jordan", "Head of property management"


def h(actor):
    return {"X-Actor": actor}


def refusals(client):
    return [a for a in client.get("/api/work-orders").json()["audit"] if a["outcome"] == "refused"]


def current(client):
    return client.get("/api/work-orders").json()["tenancies"][0]["tenancy_id"]


def raise_(client, actor, quote, tenancy=None):
    return client.post("/api/work-orders", headers=h(actor), json={
        "tenancy_id": tenancy or current(client), "category": "Plumbing", "priority": "routine",
        "description": "Replace the hot water system relief valve.", "quote_cents": quote})


def test_at_or_under_the_limit_is_approved_and_recorded(client):
    r = raise_(client, AV, ref.WO_AUTO_LIMIT_CENTS).json()
    assert r["status"] == "approved"
    wo = [o for o in client.get("/api/work-orders").json()["orders"] if o["wo_id"] == r["wo_id"]][0]
    assert wo["decided_by"] == "within the agreed limit"


def test_nobody_decides_their_own(client):
    wo = raise_(client, AV, 900_00).json()["wo_id"]
    before = len(refusals(client))
    r = client.post(f"/api/work-orders/{wo}/decide", headers=h(AV), json={"approve": True, "note": "Fine by me."})
    assert r.status_code == 403 and "cannot decide it" in r.json()["detail"]
    assert len(refusals(client)) == before + 1
    assert client.post(f"/api/work-orders/{wo}/decide", headers=h(JO), json={"approve": True, "note": "Like for like."}).json()["status"] == "approved"


def test_only_the_head_approves_over_the_higher_limit(client):
    wo = raise_(client, AV, ref.WO_HEAD_LIMIT_CENTS + 100).json()["wo_id"]
    r = client.post(f"/api/work-orders/{wo}/decide", headers=h(JO), json={"approve": True, "note": "Looks right."})
    assert r.status_code == 403 and "head of property management" in r.json()["detail"]
    # Anyone else may still reject it.
    assert client.post(f"/api/work-orders/{wo}/decide", headers=h(HEAD), json={"approve": True, "note": "Owner agreed."}).json()["status"] == "approved"


def test_a_decision_needs_a_reason(client):
    wo = raise_(client, AV, 900_00).json()["wo_id"]
    assert client.post(f"/api/work-orders/{wo}/decide", headers=h(JO), json={"approve": True, "note": "ok"}).status_code == 422


def test_cost_well_over_quote_needs_a_reason(client):
    wo = raise_(client, AV, 400_00).json()["wo_id"]
    over = 400_00 * (100 + ref.WO_VARIANCE_PCT) // 100 + 100
    r = client.post(f"/api/work-orders/{wo}/complete", headers=h(AV), json={"cost_cents": over})
    assert r.status_code == 422 and "Say why" in r.json()["detail"]
    ok = client.post(f"/api/work-orders/{wo}/complete", headers=h(AV), json={"cost_cents": over, "note": "Second valve also failed on the day."})
    assert ok.json()["status"] == "completed"


def test_only_approved_work_is_completed(client):
    wo = raise_(client, AV, 900_00).json()["wo_id"]
    r = client.post(f"/api/work-orders/{wo}/complete", headers=h(AV), json={"cost_cents": 900_00})
    assert r.status_code == 409


def test_an_ended_tenancy_is_refused(client):
    ended = client.get("/api/work-orders").json()["ended_example"]
    r = raise_(client, AV, 300_00, tenancy=ended)
    assert r.status_code == 409 and "ended" in r.json()["detail"]


def test_strangers_and_unknown_tenancies_are_refused(client):
    assert raise_(client, "Visitor", 300_00).status_code == 403
    assert raise_(client, AV, 300_00, tenancy="T-999999").status_code == 404


def test_seeded_history_shows_each_rule_refusing(built):
    details = " ".join(r[0] for r in built.execute("SELECT detail FROM audit_log WHERE outcome = 'refused'").fetchall())
    for phrase in ("cannot decide it", "only the head of property management", "Say why", "ended on"):
        assert phrase in details
