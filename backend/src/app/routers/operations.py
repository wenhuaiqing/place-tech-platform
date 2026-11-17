"""The production gate, monitoring and triage, and cost."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.app.gate import rules
from src.app.pipeline import cost as cost_model
from src.app.pipeline import monitoring as mon
from src.app.pipeline import reference as ref
from src.app.routers.platform import eval_status
from src.app.services import changes, db, llm, triage
from src.app.services.auth import actor, require_write
from src.app.services.rate_limit import enforce_orb_rate_limit
from src.settings import REPO_ROOT, settings

router = APIRouter(prefix="/api", tags=["operations"])


# ---- The production gate ------------------------------------------------------------

@router.get("/gate")
def gate() -> dict:
    return {
        "rules": [{"rule_id": k, "name": v[0], "what": v[1]} for k, v in rules.RULES.items()],
        "results": db.rows("""SELECT t.tool_id, t.name, t.tier, t.users_30d, t.data_classes, t.home, t.status, g.outcome, g.refuse_count, g.hold_count,
                                     g.scanned_files, (SELECT string_agg(DISTINCT rule_id, ', ' ORDER BY rule_id) FROM gate_finding f WHERE f.tool_id = t.tool_id) AS rules,
                                     (SELECT count(*) FROM repo_fix x WHERE x.repo = t.repo OR t.repo_candidates LIKE '%' || x.repo || '%') AS fixes
                              FROM tool t JOIN gate_result g USING (tool_id)
                              ORDER BY CASE g.outcome WHEN 'refuse' THEN 0 WHEN 'hold' THEN 1 ELSE 2 END, t.tier, t.users_30d DESC"""),
        "by_rule": db.rows("""SELECT rule_id, count(DISTINCT tool_id) AS tools, sum((outcome = 'refuse')::INT) AS refusals,
                                     sum((outcome = 'hold')::INT) AS holds FROM gate_finding GROUP BY 1 ORDER BY 1"""),
        "ablation": db.rows("SELECT * FROM gate_ablation ORDER BY personal_records_exposed DESC, tools_through DESC"),
        "registry_size": len(ref.REGISTRY_SNAPSHOT), "advisories": [{"id": a, "package": p, "fixed_in": f, "severity": s} for a, p, f, s, _ in ref.ADVISORIES],
    }


@router.get("/gate/{tool_id}")
def gate_tool(tool_id: str) -> dict:
    t = db.rows("SELECT tool_id, name, repo, repo_candidates, data_classes, users_30d, records, home, status FROM tool WHERE tool_id = ?", [tool_id])
    if not t:
        raise HTTPException(404, "No such tool.")
    repo = t[0]["repo"]
    repos = [repo] if repo else [r.strip() for r in (t[0]["repo_candidates"] or "").split(",") if r.strip()]
    marks = ", ".join("?" * len(repos)) or "''"
    return {
        "tool": t[0],
        "result": (db.rows("SELECT * FROM gate_result WHERE tool_id = ?", [tool_id]) or [None])[0],
        "findings": db.rows("SELECT rule_id, outcome, path, line, evidence, detail FROM gate_finding WHERE tool_id = ? ORDER BY outcome DESC, rule_id", [tool_id]),
        "files": db.rows(f"SELECT repo, path, in_head, commit_sha, committed_at, length(content) AS bytes FROM src_repo_files WHERE repo IN ({marks}) ORDER BY in_head DESC, repo, path", repos),
        "fixes": db.rows(f"SELECT repo, path, note FROM repo_fix WHERE repo IN ({marks}) ORDER BY path", repos),
        "rotations": db.rows("SELECT fingerprint, rotated_at, rotated_by FROM secret_rotation WHERE tool_id = ?", [tool_id]),
    }


@router.get("/gate/{tool_id}/file")
def gate_file(tool_id: str, path: str, head: bool = True) -> dict:
    t = db.rows("SELECT repo, repo_candidates FROM tool WHERE tool_id = ?", [tool_id])
    if not t:
        raise HTTPException(404, "No such tool.")
    repos = [t[0]["repo"]] if t[0]["repo"] else [r.strip() for r in (t[0]["repo_candidates"] or "").split(",")]
    rows = db.rows(f"SELECT repo, path, content FROM src_repo_files WHERE repo IN ({', '.join('?' * len(repos))}) AND path = ? AND in_head = ? LIMIT 1",
                   [*repos, path, head])
    if not rows:
        raise HTTPException(404, "No such file.")
    content = rows[0]["content"]
    # Shown masked: the page demonstrates the finding, it does not republish the key.
    for _line, _kind, value in rules.secrets_in(path, content):
        content = content.replace(value, rules.mask(value))
    return {"repo": rows[0]["repo"], "path": path, "content": content}


class Snippet(BaseModel):
    path: str = Field(default="netlify/functions/handler.js", max_length=120)
    content: str = Field(max_length=8000)
    personal: bool = True


@router.post("/gate/try", dependencies=[Depends(enforce_orb_rate_limit)])
def gate_try(body: Snippet) -> dict:
    """Run the checks over pasted code. Runs nothing and stores nothing."""
    files = [(body.path, body.content, True)]
    ctx = rules.Context(data_classes={"personal"} if body.personal else {"public"})
    findings = rules.scan(files, ctx)
    return {"outcome": rules.outcome(findings),
            "findings": [{"rule_id": f.rule_id, "name": rules.RULES[f.rule_id][0], "outcome": f.outcome, "line": f.line,
                          "evidence": f.evidence, "detail": f.detail} for f in findings]}


@router.post("/gate/{tool_id}/fix", dependencies=[Depends(require_write)])
def gate_fix(tool_id: str, request: Request) -> dict:
    with db.writing() as cur:
        return changes.apply_fix(cur, actor(request), tool_id)


@router.post("/gate/{tool_id}/rotate", dependencies=[Depends(require_write)])
def gate_rotate(tool_id: str, request: Request) -> dict:
    with db.writing() as cur:
        return changes.record_rotation(cur, actor(request), tool_id)


# ---- Monitoring -------------------------------------------------------------------------

@router.get("/monitoring")
def monitoring() -> dict:
    names = {r["site"]: r["name"] for r in db.rows("SELECT site, name FROM tool WHERE site IS NOT NULL")}
    pages = db.rows("SELECT * FROM page ORDER BY opened_at")
    for p in pages:
        p["tool_name"] = names.get(p["tool_key"], p["tool_key"])
    return {
        "window": {"from": ref.ALERT_START.isoformat(), "days": ref.ALERT_DAYS},
        "tools": [{"key": mon.resource(k), "name": names.get(mon.resource(k), k)} for k in ref.MONITORED],
        "decisions": db.rows("SELECT rule, count(*) AS alerts FROM alert_decision GROUP BY 1 ORDER BY 2 DESC"),
        "ablation": db.rows("SELECT * FROM noise_ablation"),
        "pages": pages,
        "daily": db.rows("""SELECT CAST(r.ts AS DATE) AS day, count(*) AS alerts, count(DISTINCT d.page_id) FILTER (WHERE d.rule = 'paged') AS pages
                            FROM alert_raw r JOIN alert_decision d USING (alert_id) GROUP BY 1 ORDER BY 1"""),
        "by_signal": db.rows("SELECT signal, count(*) AS alerts FROM alert_raw GROUP BY 1 ORDER BY 2 DESC"),
        "forecasts": db.rows("SELECT * FROM forecast ORDER BY days_left NULLS LAST"),
        "maintenance": "%02d:%02d to %02d:%02d" % ref.MAINTENANCE,
    }


@router.get("/monitoring/pages/{page_id}")
def page_detail(page_id: str) -> dict:
    p = db.rows("SELECT * FROM page WHERE page_id = ?", [page_id])
    if not p:
        raise HTTPException(404, "No such page.")
    w = db.rows("SELECT incident_id, summary, world FROM incident_world WHERE page_id = ?", [page_id])
    world = json.loads(w[0]["world"]) if w else mon.world_for(db.connection().cursor(), p[0]["tool_key"],
                                                               _ts(p[0]["opened_at"]), _ts(p[0]["closed_at"]))
    return {"page": p[0], "summary": w[0]["summary"] if w else None, "case_id": w[0]["incident_id"] if w else None, "world": world,
            "alerts": db.rows("""SELECT r.alert_id, r.ts, r.monitor, r.signal, r.region, r.value, r.threshold FROM alert_raw r
                                 JOIN alert_decision d USING (alert_id) WHERE d.page_id = ? ORDER BY r.ts""", [page_id])}


def _ts(v):
    from datetime import datetime
    return datetime.fromisoformat(v) if isinstance(v, str) else v


def _runbook_grades() -> dict:
    from src.app.services.triage_cases import build_cases
    cases = build_cases(db.raw("SELECT * FROM incident_world ORDER BY incident_id"))
    rows = []
    for cs in cases:
        run = triage.run_rules(cs["case"])
        g = triage.grade(run, cs["label"])
        rows.append({"case_id": cs["case_id"], "kind": cs["kind"], "label": cs["label"], "why": cs.get("why"),
                     "category": run["result"]["category"], "action": run["result"]["proposed_action"], "passed": g["passed"], "harmful": g["harmful"]})
    by_kind = {}
    for r in rows:
        k = by_kind.setdefault(r["kind"], {"cases": 0, "passed": 0})
        k["cases"] += 1
        k["passed"] += r["passed"]
    return {"cases": len(rows), "passed": sum(r["passed"] for r in rows), "harmful": sum(r["harmful"] for r in rows),
            "by_kind": by_kind, "results": rows}


@router.get("/triage")
def triage_page() -> dict:
    status = eval_status()
    return {"runbook": _runbook_grades(),"configured": llm.configured(), "model": settings.llm_chat_model if llm.configured() else None,
            "fallback_model": settings.llm_fallback_model or None, "eval": status, "categories": triage.ACTION_FOR,
            "runbook_map": triage.RUNBOOK, "tools": triage.TOOL_DOCS, "system_prompt": triage.SYSTEM,
            "cases": db.rows("SELECT incident_id, page_id, tool_key, opened_at, summary FROM incident_world ORDER BY opened_at")}


@router.post("/triage/{incident_id}/run", dependencies=[Depends(enforce_orb_rate_limit)])
async def triage_run(incident_id: str, engine: str = "agent") -> dict:
    """Triage one page live. The agent reads only the frozen snapshot and writes nothing."""
    rows = db.rows("SELECT * FROM incident_world WHERE incident_id = ?", [incident_id])
    if not rows:
        raise HTTPException(404, "No such page.")
    case = {"page_id": rows[0]["page_id"], "tool": rows[0]["tool_key"], "opened_at": rows[0]["opened_at"],
            "summary": rows[0]["summary"], "world": json.loads(rows[0]["world"])}
    if engine == "agent" and llm.configured():
        try:
            run = await run_in_threadpool(triage.run_agent, case)
        except Exception as exc:  # noqa: BLE001 - say so, then fall back
            run = triage.run_rules(case)
            run["fallback_reason"] = f"The model did not answer ({type(exc).__name__}); the runbook answered instead."
    else:
        run = triage.run_rules(case)
        if engine == "agent":
            run["fallback_reason"] = "No model key on this deployment; the runbook answered."
    run.pop("retrieved", None)
    return run


# ---- The paved road ---------------------------------------------------------------------

@router.get("/paved-road")
def paved_road() -> dict:
    """The template every tool moves into, read from paved-road/ in this repository."""
    root = REPO_ROOT / "paved-road"
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            files.append({"path": p.relative_to(root).as_posix(), "content": p.read_text(encoding="utf-8")})
    return {"files": files}


# ---- Cost --------------------------------------------------------------------------------

@router.get("/cost")
def cost() -> dict:
    last = ref.BILLING_MONTHS[-1]
    return {
        "months": ref.BILLING_MONTHS, "aud_per_usd": ref.AUD_PER_USD_BP / 10_000,
        "by_month": db.rows("SELECT month, platform, sum(aud_cents) AS aud_cents FROM cost_line GROUP BY 1, 2 ORDER BY 1, 2"),
        "by_tool": db.rows(f"""SELECT t.tool_id, t.name, t.users_30d, t.paid_by, t.status, sum(c.aud_cents) AS aud_cents,
                                      string_agg(DISTINCT c.platform, ', ') AS platforms
                               FROM cost_line c JOIN tool t USING (tool_id) WHERE c.month = '{last}' GROUP BY ALL ORDER BY aud_cents DESC"""),
        "unattributed": db.rows(f"""SELECT platform, resource, basis, aud_cents FROM cost_line WHERE month = '{last}' AND tool_id IS NULL
                                    ORDER BY aud_cents DESC"""),
        "findings": db.rows("SELECT * FROM cost_finding ORDER BY monthly_aud_cents DESC"),
        "paid_by": db.rows("SELECT paid_by, count(*) AS tools, sum(monthly_cost_aud_cents) AS aud_cents FROM tool GROUP BY 1 ORDER BY 3 DESC"),
        "target": [{"item": i, "aud_cents": c} for i, c in cost_model.TARGET_PLAN],
        "drift": db.rows("""SELECT a.name, a.type, a.monthly_aud_cents, a.name IN (SELECT name FROM src_tf_state) AS in_terraform
                            FROM src_azure_resources a ORDER BY in_terraform, a.monthly_aud_cents DESC"""),
    }
