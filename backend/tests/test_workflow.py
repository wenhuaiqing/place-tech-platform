"""Governed writes: who may do what, refused and audit-logged when not."""

from __future__ import annotations

from tests.conftest import as_


def tid(client, name):
    return [t for t in client.get("/api/register").json()["tools"] if t["name"] == name][0]["tool_id"]


def refusals(client):
    return [a for a in client.get("/api/audit").json() if a["outcome"] == "refused"]


def test_proposer_cannot_decide_and_non_cab_cannot_decide(client):
    t = tid(client, "Key register")
    cr = client.post("/api/changes", json={"tool_id": t, "kind": "migrate", "reason": "Small tool, good first move."},
                     headers=as_("CAB - Business Systems")).json()["cr_id"]
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "fine"}, headers=as_("CAB - Business Systems"))
    assert r.status_code == 403 and "cannot decide it" in r.json()["detail"]
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "fine"}, headers=as_("Builder - Mia K."))
    assert r.status_code == 403
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "Agreed."}, headers=as_("CAB - Head of Innovation"))
    assert r.json()["status"] == "approved"
    assert len(refusals(client)) >= 2


def test_release_refused_until_migrated_and_gate_passes(client):
    t = tid(client, "Rental arrears tracker")
    cr = client.post("/api/changes", json={"tool_id": t, "kind": "release", "reason": "Ready for the platform."},
                     headers=as_("Platform lead")).json()["cr_id"]
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "Agreed."}, headers=as_("CAB - Head of Innovation"))
    assert r.status_code == 409 and "personal accounts" in r.json()["detail"]


def test_fix_then_rotation_then_migrate_and_release(client):
    t = tid(client, "Rental arrears tracker")
    assert client.post(f"/api/gate/{t}/rotate", headers=as_("Platform lead")).status_code == 409  # still in the code
    assert client.post(f"/api/gate/{t}/fix", headers=as_("Builder - Mia K.")).json()["gate"] == "refuse"
    assert client.post(f"/api/gate/{t}/fix", headers=as_("Builder - Mia K.")).status_code == 409  # nothing left to apply
    assert client.post(f"/api/gate/{t}/rotate", headers=as_("Builder - Mia K.")).status_code == 403
    assert client.post(f"/api/gate/{t}/rotate", headers=as_("Platform lead")).json()["gate"] == "pass"
    for kind in ("migrate", "release"):
        cr = client.post("/api/changes", json={"tool_id": t, "kind": kind, "reason": "Fixed, rotated and ready."},
                         headers=as_("Builder - Mia K.")).json()["cr_id"]
        assert client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "Agreed."},
                           headers=as_("CAB - Business Systems")).status_code == 200
        assert client.post(f"/api/changes/{cr}/implement", headers=as_("CAB - Business Systems")).status_code == 403
        assert client.post(f"/api/changes/{cr}/implement", headers=as_("Platform lead")).json()["status"] == "implemented"
    tool = client.get(f"/api/register/{t}").json()["tool"]
    assert tool["home"] == "place-github" and tool["status"] == "in production on Place platform"


def test_retire_refused_while_in_use_and_migrate_needs_an_owner(client):
    used = tid(client, "Leads inbox summariser")
    cr = client.post("/api/changes", json={"tool_id": used, "kind": "retire", "reason": "Connector to personal storage."},
                     headers=as_("Platform lead")).json()["cr_id"]
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "Agreed."}, headers=as_("CAB - Head of Innovation"))
    assert r.status_code == 409 and "used" in r.json()["detail"]
    orphan = tid(client, "lease-renewals-a91e")
    cr = client.post("/api/changes", json={"tool_id": orphan, "kind": "migrate", "reason": "Move it into the org."},
                     headers=as_("Platform lead")).json()["cr_id"]
    r = client.post(f"/api/changes/{cr}/decide", json={"approve": True, "note": "Agreed."}, headers=as_("CAB - Head of Innovation"))
    assert r.status_code == 409 and "Transfer ownership first" in r.json()["detail"]


def test_duplicate_open_change_refused_and_reason_required(client):
    t = tid(client, "Weekend roster")
    assert client.post("/api/changes", json={"tool_id": t, "kind": "migrate", "reason": "short"}, headers=as_("Platform lead")).status_code == 422
    assert client.post("/api/changes", json={"tool_id": t, "kind": "migrate", "reason": "Move it into the org."}, headers=as_("Platform lead")).status_code == 200
    assert client.post("/api/changes", json={"tool_id": t, "kind": "migrate", "reason": "Move it into the org."}, headers=as_("Platform lead")).status_code == 409


def test_reset_needs_the_token(client):
    assert client.post("/api/reset", headers={"X-Actor": "Platform lead"}).status_code == 401
    assert client.post("/api/reset", headers=as_("Platform lead")).status_code == 200


def test_seeded_history_shows_the_rules_working(built):
    refused = built.execute("SELECT detail FROM audit_log WHERE outcome = 'refused' ORDER BY audit_id").fetchall()
    assert any("cannot decide it" in r[0] for r in refused)
    assert any("personal accounts" in r[0] for r in refused)
