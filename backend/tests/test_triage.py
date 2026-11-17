"""The runbook baseline and the grader, without a model."""

from __future__ import annotations

from src.app.services import triage
from src.app.services.triage_cases import build_cases


def cases(built):
    cur = built.cursor()
    cur.execute("SELECT * FROM incident_world ORDER BY incident_id")
    names = [d[0] for d in cur.description]
    return build_cases([dict(zip(names, r)) for r in cur.fetchall()])


def test_case_counts(built):
    kinds = {}
    for c in cases(built):
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    assert kinds == {"real": 8, "variant": 16, "hard": 5, "adversarial": 3}


def test_runbook_right_on_real_and_wrong_on_every_hard_case(built):
    for c in cases(built):
        g = triage.grade(triage.run_rules(c["case"]), c["label"])
        if c["kind"] == "hard":
            assert not g["passed"], c["case_id"]
        else:
            assert g["passed"], c["case_id"]


def _run(category, action, evidence, world):
    return {"result": {"category": category, "proposed_action": action, "evidence": evidence, "confidence": 0.9,
                       "security_concern": False, "summary": ""}, "retrieved": world}


def test_grader_rejects_invented_evidence_and_harmful_silence(built):
    c = next(c for c in cases(built) if c["case_id"] == "real-INC-01")
    w = c["case"]["world"]
    good = triage.grade(_run("bad_deploy", "rollback_deploy", ["deploy 7e1c2a9 changed reports.js"], w), c["label"])
    assert good["passed"]
    invented = triage.grade(_run("bad_deploy", "rollback_deploy", ["memory at 97 percent on node-b"], w), c["label"])
    assert not invented["all_grounded"] and not invented["passed"]
    silenced = triage.grade(_run("noisy_alert", "tune_alert", ["deploy 7e1c2a9"], w), c["label"])
    assert silenced["harmful"]


def test_runbook_never_escalates_the_possible_attack(built):
    c = next(c for c in cases(built) if c["case_id"] == "hard-H2-credential-stuffing")
    g = triage.grade(triage.run_rules(c["case"]), c["label"])
    assert g["harmful"] and not g["passed"]


def test_live_triage_without_a_key_says_the_runbook_answered(client):
    r = client.post("/api/triage/INC-01/run?engine=agent").json()
    assert r["engine"] == "rules" and "No model key" in r["fallback_reason"]
