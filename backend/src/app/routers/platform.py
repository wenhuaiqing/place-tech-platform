"""What the deployment is, the overview, the audit log, reset, and the CAB report."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, Request

from src.app.pipeline import acceptance
from src.app.pipeline import reference as ref
from src.app.services import audit, db, llm
from src.app.services.auth import actor, require_write_token
from src.settings import REPO_ROOT, settings

router = APIRouter(prefix="/api", tags=["platform"])
STARTED = time.time()
EVAL_STATUS = REPO_ROOT / "evals" / "status.json"


def eval_status() -> dict | None:
    return json.loads(EVAL_STATUS.read_text(encoding="utf-8")) if EVAL_STATUS.exists() else None


@router.get("/meta")
def meta() -> dict:
    return {
        "version": settings.git_sha or "dev", "uptime_seconds": int(time.time() - STARTED), "synthetic_data": True,
        "today": ref.DEMO_TODAY.isoformat(), "exports_taken": ref.EXPORTS_TAKEN.isoformat(),
        "llm_configured": llm.configured(), "llm_model": settings.llm_chat_model if llm.configured() else None,
        "writes_public": settings.public_writes, "build_seconds": db.kv("build_seconds"),
        "people": ref.PEOPLE, "aud_per_usd": ref.AUD_PER_USD_BP / 10_000,
    }


@router.get("/overview")
def overview() -> dict:
    one = db.scalar
    ev = eval_status()
    return {
        "tools": one("SELECT count(*) FROM tool"),
        "declared": one("SELECT count(*) FROM tool WHERE declared"),
        "in_use": one("SELECT count(*) FROM tool WHERE users_30d > 0 AND status NOT IN ('retired', 'merged')"),
        "users": one("SELECT sum(users_30d) FROM tool WHERE status NOT IN ('retired', 'merged')"),
        "personal_accounts": one("SELECT count(*) FROM tool WHERE home = 'personal accounts' AND status NOT IN ('retired', 'merged')"),
        "place_github": one("SELECT count(*) FROM tool WHERE home = 'place-github'"),
        "holds": one("SELECT count(*) FROM discovery_hold WHERE resolved_by IS NULL"),
        "critical_flags": one("SELECT count(*) FROM register_flag WHERE severity = 'critical'"),
        "gate": dict(db.query("SELECT outcome, count(*) n FROM gate_result GROUP BY 1").values.tolist()),
        "personal_records_refused": one("""SELECT sum(t.records) FROM tool t JOIN gate_result g USING (tool_id)
                                           WHERE g.outcome = 'refuse' AND regexp_matches(t.data_classes, 'personal|sensitive|financial')"""),
        "alerts": one("SELECT count(*) FROM alert_raw"), "pages": one("SELECT count(*) FROM page"),
        "incidents": len(ref.INCIDENTS), "incidents_paged": one("SELECT incidents_paged FROM noise_ablation WHERE rule = 'All rules'"),
        "monthly_cost": one(f"SELECT sum(aud_cents) FROM cost_line WHERE month = '{ref.BILLING_MONTHS[-1]}'"),
        "removable": one("SELECT sum(monthly_aud_cents) FROM cost_finding WHERE kind IN ('idle', 'oversized', 'duplicate', 'drift')"),
        "changes": dict(db.query("SELECT status, count(*) n FROM change_request GROUP BY 1").values.tolist()),
        "refusals": one("SELECT count(*) FROM audit_log WHERE outcome = 'refused'"),
        "agent": (ev or {}).get("summary"),
        "acceptance": [name for name, _ in acceptance.CHECKS],
    }


@router.get("/audit")
def audit_all(system: str | None = None) -> list[dict]:
    where, params = ("WHERE system = ?", [system]) if system else ("", [])
    return db.rows(f"""SELECT ts, actor, system, project_id, subject, action, outcome, detail FROM audit_log
                       {where} ORDER BY audit_id DESC LIMIT 300""", params)


@router.post("/reset", dependencies=[Depends(require_write_token)])
def reset(request: Request) -> dict:
    """Back to the built state: every change, fix and rotation made in the demo is discarded."""
    db.reset_to_build()
    with db.writing() as cur:
        audit.record(cur, actor(request), "platform", "demo", "reset to built state")
    return {"reset": True}


@router.get("/cab")
def cab_report() -> dict:
    """The fortnightly CAB report, assembled from the data on request."""
    one = db.scalar
    since = "TIMESTAMP '2026-11-02 00:00:00'"
    return {
        "period": {"from": "2026-11-02", "to": ref.DEMO_TODAY.isoformat()},
        "register": {
            "tools": one("SELECT count(*) FROM tool"), "undeclared": one("SELECT count(*) FROM tool WHERE NOT declared"),
            "tier1": one("SELECT count(*) FROM tool WHERE tier = 1"),
            "orphaned": one("SELECT count(*) FROM register_flag WHERE flag = 'orphaned'"),
            "holds": db.rows("SELECT hold_id, source, ref, reason FROM discovery_hold WHERE resolved_by IS NULL ORDER BY hold_id"),
            "personal_accounts": one("SELECT count(*) FROM tool WHERE home = 'personal accounts' AND status NOT IN ('retired', 'merged')"),
            "place_github": one("SELECT count(*) FROM tool WHERE home = 'place-github'"),
        },
        "changes": db.rows(f"""SELECT cr_id, title, kind, proposed_by, proposed_at, status, decided_by, decided_at, decision_note,
                                      implemented_at FROM change_request ORDER BY cr_id"""),
        "refusals": db.rows(f"""SELECT ts, actor, project_id, action, detail FROM audit_log WHERE outcome = 'refused' AND ts >= {since}
                                ORDER BY ts"""),
        "gate": {
            "by_outcome": db.rows("SELECT outcome, count(*) AS tools FROM gate_result GROUP BY 1 ORDER BY 1"),
            "top_rules": db.rows("""SELECT f.rule_id, count(DISTINCT f.tool_id) AS tools, max(f.outcome) AS outcome FROM gate_finding f
                                    GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 6"""),
        },
        "operations": {
            "alerts": one("SELECT count(*) FROM alert_raw"), "pages": one("SELECT count(*) FROM page"),
            "incidents": db.rows("SELECT incident_id, tool_key, opened_at, first_signal FROM incident_world WHERE incident_id LIKE 'INC%' ORDER BY opened_at"),
            "forecasts": db.rows("SELECT resource, kind, days_left, due_on FROM forecast WHERE days_left <= 45 ORDER BY days_left"),
        },
        "cost": {
            "month": ref.BILLING_MONTHS[-1],
            "total": one(f"SELECT sum(aud_cents) FROM cost_line WHERE month = '{ref.BILLING_MONTHS[-1]}'"),
            "previous": one(f"SELECT sum(aud_cents) FROM cost_line WHERE month = '{ref.BILLING_MONTHS[-2]}' AND platform <> 'azure'"),
            "removable": one("SELECT sum(monthly_aud_cents) FROM cost_finding WHERE kind IN ('idle', 'oversized', 'duplicate', 'drift')"),
            "findings": db.rows("SELECT kind, resource, monthly_aud_cents, action FROM cost_finding ORDER BY monthly_aud_cents DESC LIMIT 8"),
        },
        "ai": db.rows("SELECT entry, approved, users, tools FROM ai_register WHERE NOT approved ORDER BY users DESC"),
    }
