"""The tool register, discovery, the AI register and the changes CAB decides."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.app.pipeline import reference as ref
from src.app.services import changes, db
from src.app.services.auth import actor, require_write

router = APIRouter(prefix="/api", tags=["register"])


@router.get("/register")
def register() -> dict:
    tools = db.rows("""SELECT t.tool_id, t.name, t.declared, t.process, t.kind, t.owner_name, t.owner_role, t.office, t.owner_status,
                              t.hosting, t.database, t.ai_route, t.users_30d, t.records, t.data_classes, t.tier, t.tier_reason,
                              t.monthly_cost_aud_cents, t.paid_by, t.home, t.status, t.sources, g.outcome AS gate,
                              (SELECT string_agg(flag, ', ' ORDER BY flag) FROM register_flag f WHERE f.tool_id = t.tool_id) AS flags
                       FROM tool t LEFT JOIN gate_result g USING (tool_id) ORDER BY t.tier, t.users_30d DESC, t.name""")
    return {"tools": tools,
            "flags": db.rows("""SELECT f.tool_id, t.name, f.flag, f.severity, f.detail FROM register_flag f LEFT JOIN tool t USING (tool_id)
                                ORDER BY CASE f.severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, f.flag, t.name"""),
            "offices": db.rows("SELECT coalesce(office, 'Unknown') AS office, count(*) AS tools, sum(users_30d) AS users FROM tool GROUP BY 1 ORDER BY 2 DESC")}


@router.get("/register/discovery")
def discovery() -> dict:
    exports = [
        ("HR feed (managed service provider)", "src_staff", "who works here, who has left"),
        ("Inventory survey", "src_survey", "what builders say they made"),
        ("GitHub (personal accounts)", "src_github_repos", "the code"),
        ("Netlify", "src_netlify_sites", "sites, their repositories and domains"),
        ("Firebase", "src_firebase_projects", "projects and their collections"),
        ("Supabase", "src_supabase_projects", "databases and their tables"),
        ("Copilot Studio", "src_copilot_agents", "agents, owners and connectors"),
        ("DNS", "src_dns", "names staff type"),
        ("Platform billing", "src_billing", "what each account is charged (US$)"),
        ("Expense claims", "src_expenses", "who pays, on a personal card"),
    ]
    return {
        "exports": [{"name": n, "rows": db.scalar(f"SELECT count(*) FROM {t}"), "gives": g} for n, t, g in exports],
        "joins": db.rows("SELECT joined_by, count(*) AS links FROM tool_source WHERE joined_by <> 'anchor' GROUP BY 1 ORDER BY 2 DESC"),
        "holds": db.rows("SELECT * FROM discovery_hold ORDER BY hold_id"),
        "dangling": db.rows("SELECT detail FROM register_flag WHERE flag = 'dangling_dns'"),
        "renamed": db.rows("""SELECT t.tool_id, t.name, t.site, t.repo FROM tool t
                              WHERE t.hosting = 'netlify' AND t.repo IS NOT NULL AND t.site <> split_part(t.repo, '/', 2) ORDER BY t.name"""),
        "survey_vs_measured": db.rows("""SELECT t.name, s.users_estimate, t.users_30d FROM tool t JOIN src_survey s ON s.tool_name = t.name
                                         WHERE t.kind <> 'script' ORDER BY abs(s.users_estimate - t.users_30d) DESC LIMIT 6"""),
    }


@router.get("/register/ai")
def ai_register() -> dict:
    return {"entries": db.rows("SELECT * FROM ai_register ORDER BY approved, users DESC"),
            "policy": [{"route": k, "approved": v[0], "data_allowed": v[1]} for k, v in ref.APPROVED_AI_TOOLS.items()],
            "gateway": ref.APPROVED_AI_HOSTS[0]}


@router.get("/register/{tool_id}")
def tool(tool_id: str) -> dict:
    t = db.rows("SELECT * FROM tool WHERE tool_id = ?", [tool_id])
    if not t:
        raise HTTPException(404, "No such tool.")
    return {
        "tool": t[0],
        "sources": db.rows("SELECT source, ref, joined_by FROM tool_source WHERE tool_id = ? ORDER BY source", [tool_id]),
        "flags": db.rows("SELECT flag, severity, detail FROM register_flag WHERE tool_id = ?", [tool_id]),
        "gate": db.rows("SELECT outcome, refuse_count, hold_count, scanned_files FROM gate_result WHERE tool_id = ?", [tool_id]),
        "findings": db.rows("SELECT rule_id, outcome, path, line, evidence, detail FROM gate_finding WHERE tool_id = ? ORDER BY outcome DESC, rule_id", [tool_id]),
        "cost": db.rows("SELECT month, sum(aud_cents) AS aud_cents FROM cost_line WHERE tool_id = ? GROUP BY 1 ORDER BY 1", [tool_id]),
        "changes": db.rows("SELECT cr_id, title, status, proposed_by, decided_by FROM change_request WHERE tool_id = ? ORDER BY cr_id", [tool_id]),
    }


# ---- Changes -------------------------------------------------------------------------

class Proposal(BaseModel):
    tool_id: str = Field(max_length=10)
    kind: str = Field(max_length=20)
    target: str | None = Field(default=None, max_length=80)
    reason: str = Field(max_length=500)


class Decision(BaseModel):
    approve: bool
    note: str = Field(max_length=500)


@router.get("/changes")
def list_changes() -> dict:
    rows = db.rows("SELECT * FROM change_request ORDER BY cr_id DESC")
    for r in rows:
        r["evidence"] = json.loads(r["evidence"]) if r["evidence"] else None
    return {"changes": rows, "kinds": changes.KINDS, "cab": sorted(ref.CAB_MEMBERS), "implementers": sorted(ref.IMPLEMENTERS),
            "staff": db.rows("""SELECT upn, display_name, role, office FROM src_staff WHERE status = 'active' AND upn NOT LIKE 's0%' ORDER BY display_name"""),
            "tools": db.rows("SELECT tool_id, name, status FROM tool WHERE status NOT IN ('retired', 'merged') ORDER BY name"),
            "audit": db.rows("SELECT ts, actor, project_id, subject, action, outcome, detail FROM audit_log WHERE system IN ('change', 'gate') ORDER BY audit_id DESC LIMIT 60")}


@router.post("/changes", dependencies=[Depends(require_write)])
def propose(body: Proposal, request: Request) -> dict:
    with db.writing() as cur:
        return changes.propose(cur, actor(request), body.tool_id, body.kind, body.target, body.reason)


@router.post("/changes/{cr_id}/decide", dependencies=[Depends(require_write)])
def decide(cr_id: str, body: Decision, request: Request) -> dict:
    with db.writing() as cur:
        return changes.decide(cur, actor(request), cr_id, body.approve, body.note)


@router.post("/changes/{cr_id}/implement", dependencies=[Depends(require_write)])
def implement(cr_id: str, request: Request) -> dict:
    with db.writing() as cur:
        return changes.implement(cur, actor(request), cr_id)
