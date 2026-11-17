"""Changes to the estate, the way CAB would govern them.

A change is proposed with its evidence attached by the server (the gate's
result, the register entry, what it costs and who uses it), decided by a CAB
member who did not propose it, and implemented by the platform lead. Each
rule is checked again at implementation, because the world may have moved
since the decision. A refusal is recorded in the audit log and returned as
a sentence a person can act on; nothing is a warning.

Kinds:
  migrate         move the code into Place's GitHub organisation
  release         put it into production on the Place platform (gate must pass)
  retire          switch it off (nobody may be using it)
  merge           move its users to another tool, then retire it
  transfer_owner  give it a current owner
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.app.gate import scan
from src.app.pipeline import reference as ref
from src.app.services import audit

KINDS = {
    "migrate": "Move into the Place GitHub organisation",
    "release": "Release to production on the Place platform",
    "retire": "Retire",
    "merge": "Merge into another tool",
    "transfer_owner": "Transfer ownership",
}


def _tool(cur, tool_id: str) -> dict | None:
    cur.execute("""SELECT t.tool_id, t.name, t.owner_upn, t.owner_name, t.owner_status, t.users_30d, t.tier, t.data_classes,
                          t.monthly_cost_aud_cents, t.home, t.status, g.outcome, g.refuse_count, g.hold_count
                   FROM tool t LEFT JOIN gate_result g USING (tool_id) WHERE t.tool_id = ?""", [tool_id])
    row = cur.fetchone()
    if not row:
        return None
    keys = ["tool_id", "name", "owner_upn", "owner_name", "owner_status", "users", "tier", "data_classes", "cost", "home", "status",
            "gate", "refuse", "hold"]
    return dict(zip(keys, row))


def _rule(cur, kind: str, t: dict, target: str | None) -> str | None:
    """None when the change may go ahead; otherwise why not."""
    if t["status"] in ("retired", "merged"):
        return f"{t['name']} is already {t['status']}."
    if kind == "migrate":
        if t["home"] == "place-github":
            return f"{t['name']} is already in the Place GitHub organisation."
        if t["owner_status"] != "active":
            return f"{t['name']} has no current owner ({t['owner_name'] or 'unknown'} has left). Transfer ownership first: a tool moves with someone who answers for it."
    if kind == "release":
        if t["home"] != "place-github":
            return f"{t['name']} is still on personal accounts. Migrate it into the Place GitHub organisation first."
        if t["gate"] != "pass":
            return (f"The production gate {'refuses' if t['gate'] == 'refuse' else 'holds'} {t['name']}: "
                    f"{t['refuse']} finding(s) refuse, {t['hold']} hold. Fix them and re-scan; the gate decides, not the vote.")
    if kind == "retire" and t["users"] > 0:
        return f"{t['users']} people used {t['name']} in the last 30 days. Merge it into a replacement, or tell them and wait until nobody does."
    if kind == "merge":
        if not target:
            return "A merge needs the tool it merges into."
        cur.execute("SELECT name, status FROM tool WHERE tool_id = ?", [target])
        row = cur.fetchone()
        if not row or target == t["tool_id"]:
            return "The tool to merge into does not exist, or is the same tool."
        if row[1] in ("retired", "merged"):
            return f"{row[0]} is {row[1]}; merge into a tool that is in use."
        cur.execute("SELECT outcome FROM gate_result WHERE tool_id = ?", [target])
        g = cur.fetchone()
        if g and g[0] == "refuse":
            return f"The gate refuses {row[0]}. Merging moves {t['users']} more people onto a tool that may not go to production."
    if kind == "transfer_owner":
        cur.execute("SELECT status FROM src_staff WHERE upn = ?", [target or ""])
        row = cur.fetchone()
        if not row:
            return "The new owner is not in the HR feed."
        if row[0] != "active":
            return "The new owner has left; choose someone current."
    return None


def evidence(cur, t: dict, kind: str, target: str | None) -> dict:
    cur.execute("SELECT flag, detail FROM register_flag WHERE tool_id = ?", [t["tool_id"]])
    flags = [{"flag": f, "detail": d} for f, d in cur.fetchall()]
    preview = {
        "migrate": "Code moves to the Place GitHub organisation with branch protection, CODEOWNERS and the gate in CI. Users notice nothing.",
        "release": f"{t['users']} users move to the Place platform; hosting on personal accounts stops.",
        "retire": f"Saves A${t['cost'] / 100:,.2f} a month. Nobody used it in 30 days.",
        "merge": f"{t['users']} users move to the target tool; saves A${t['cost'] / 100:,.2f} a month once retired.",
        "transfer_owner": f"{target} answers for it from now on.",
    }[kind]
    return {"gate": t["gate"], "gate_refuse": t["refuse"], "gate_hold": t["hold"], "tier": t["tier"], "users_30d": t["users"],
            "data_classes": t["data_classes"], "monthly_cost_aud_cents": t["cost"], "owner": t["owner_name"],
            "owner_status": t["owner_status"], "flags": flags, "preview": preview}


def _refuse(cur, actor, subject, action, why, status=409, cr_id=None):
    audit.refuse(cur, actor, "change", subject, action, why, project_id=cr_id, status=status)


def propose(cur, actor: str, tool_id: str, kind: str, target: str | None, reason: str, at: datetime | None = None) -> dict:
    at = at or audit.now()
    if kind not in KINDS:
        _refuse(cur, actor, tool_id, "propose", f"Unknown kind of change: {kind}.", status=422)
    t = _tool(cur, tool_id)
    if not t:
        _refuse(cur, actor, tool_id, "propose", "No such tool in the register.", status=404)
    if len((reason or "").strip()) < 10:
        _refuse(cur, actor, tool_id, "propose", "Say why, in a sentence: CAB decides on the reason as well as the evidence.", status=422)
    cur.execute("SELECT cr_id FROM change_request WHERE tool_id = ? AND kind = ? AND status IN ('submitted', 'approved')", [tool_id, kind])
    open_cr = cur.fetchone()
    if open_cr:
        _refuse(cur, actor, tool_id, "propose", f"{open_cr[0]} already proposes this change for {t['name']}.")
    cur.execute("SELECT coalesce(max(CAST(substr(cr_id, 4) AS INTEGER)), 0) + 1 FROM change_request")
    cr_id = f"CR-{cur.fetchone()[0]:03d}"
    title = f"{KINDS[kind]}: {t['name']}"
    ev = evidence(cur, t, kind, target)
    cur.execute("INSERT INTO change_request VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'submitted', NULL, NULL, NULL, NULL, NULL, ?)",
                [cr_id, tool_id, kind, target, title, reason.strip()[:500], actor, at, json.dumps(ev)])
    audit.record(cur, actor, "change", tool_id, "proposed", project_id=cr_id, detail=title, at=at)
    return {"cr_id": cr_id, "title": title, "evidence": ev}


def decide(cur, actor: str, cr_id: str, approve: bool, note: str, at: datetime | None = None) -> dict:
    at = at or audit.now()
    cur.execute("SELECT tool_id, kind, target, proposed_by, status, title FROM change_request WHERE cr_id = ?", [cr_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, cr_id, "decide", "No such change.", status=404)
    tool_id, kind, target, proposer, status, title = row
    if actor not in ref.CAB_MEMBERS:
        _refuse(cur, actor, cr_id, "decide", "Only a CAB member decides a change.", status=403, cr_id=cr_id)
    if actor == proposer:
        _refuse(cur, actor, cr_id, "decide", "You proposed this change, so you cannot decide it. Another CAB member must.", status=403, cr_id=cr_id)
    if status != "submitted":
        _refuse(cur, actor, cr_id, "decide", f"{cr_id} is {status}; only a submitted change is decided.", cr_id=cr_id)
    if len((note or "").strip()) < 5:
        _refuse(cur, actor, cr_id, "decide", "Record the reason for the decision.", status=422, cr_id=cr_id)
    if approve:
        why = _rule(cur, kind, _tool(cur, tool_id), target)
        if why:
            _refuse(cur, actor, cr_id, "approve", why, cr_id=cr_id)
    new = "approved" if approve else "rejected"
    cur.execute("UPDATE change_request SET status = ?, decided_by = ?, decided_at = ?, decision_note = ? WHERE cr_id = ?",
                [new, actor, at, note.strip()[:500], cr_id])
    audit.record(cur, actor, "change", tool_id, new, project_id=cr_id, detail=title, at=at)
    return {"cr_id": cr_id, "status": new}


def implement(cur, actor: str, cr_id: str, at: datetime | None = None) -> dict:
    at = at or audit.now()
    cur.execute("SELECT tool_id, kind, target, status, title FROM change_request WHERE cr_id = ?", [cr_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, cr_id, "implement", "No such change.", status=404)
    tool_id, kind, target, status, title = row
    if actor not in ref.IMPLEMENTERS:
        _refuse(cur, actor, cr_id, "implement", "The platform lead implements approved changes.", status=403, cr_id=cr_id)
    if status != "approved":
        _refuse(cur, actor, cr_id, "implement", f"{cr_id} is {status}; only an approved change is implemented.", cr_id=cr_id)
    why = _rule(cur, kind, _tool(cur, tool_id), target)
    if why:
        _refuse(cur, actor, cr_id, "implement", "Approved, but no longer true: " + why, cr_id=cr_id)
    if kind == "migrate":
        cur.execute("UPDATE tool SET home = 'place-github' WHERE tool_id = ?", [tool_id])
    elif kind == "release":
        cur.execute("UPDATE tool SET status = 'in production on Place platform' WHERE tool_id = ?", [tool_id])
    elif kind == "retire":
        cur.execute("UPDATE tool SET status = 'retired' WHERE tool_id = ?", [tool_id])
    elif kind == "merge":
        cur.execute("UPDATE tool SET status = 'merged' WHERE tool_id = ?", [tool_id])
    elif kind == "transfer_owner":
        cur.execute("SELECT display_name, role, office FROM src_staff WHERE upn = ?", [target])
        name, role, office = cur.fetchone()
        cur.execute("""UPDATE tool SET owner_upn = ?, owner_name = ?, owner_role = ?, office = ?, owner_status = 'active', owner_left_on = NULL
                       WHERE tool_id = ?""", [target, name, role, office, tool_id])
    cur.execute("UPDATE change_request SET status = 'implemented', implemented_by = ?, implemented_at = ? WHERE cr_id = ?", [actor, at, cr_id])
    audit.record(cur, actor, "change", tool_id, "implemented", project_id=cr_id, detail=title, at=at)
    return {"cr_id": cr_id, "status": "implemented"}


# ---- The gate's writes ----------------------------------------------------------------

def apply_fix(cur, actor: str, tool_id: str, at: datetime | None = None) -> dict[str, Any]:
    """The owner pushes the fix branch: head files replaced, old versions kept as
    history - which is exactly why a removed secret still needs rotating."""
    at = at or audit.now()
    cur.execute("SELECT repo, repo_candidates, name FROM tool WHERE tool_id = ?", [tool_id])
    row = cur.fetchone()
    if not row:
        _refuse(cur, actor, tool_id, "apply fix", "No such tool.", status=404)
    repo, candidates, name = row
    repos = [repo] if repo else [r.strip() for r in (candidates or "").split(",")]
    applied = []
    for r in repos:
        cur.execute("SELECT path, content, note FROM repo_fix WHERE repo = ? ORDER BY path", [r])
        for path, content, note in cur.fetchall():
            cur.execute("SELECT content FROM src_repo_files WHERE repo = ? AND path = ? AND in_head", [r, path])
            head = cur.fetchone()
            if head and head[0] == content:
                continue
            if not head and content == "":
                continue
            cur.execute("UPDATE src_repo_files SET in_head = false WHERE repo = ? AND path = ? AND in_head", [r, path])
            if content:
                cur.execute("INSERT INTO src_repo_files VALUES (?, ?, ?, true, ?, ?)", [r, path, content, "fix0001", at])
            applied.append({"path": path, "note": note})
    if not applied:
        _refuse(cur, actor, tool_id, "apply fix", f"There is no unapplied fix branch for {name}.")
    result = scan.scan_tool(cur, tool_id, at)
    audit.record(cur, actor, "gate", tool_id, "fix applied", detail=f"{len(applied)} file(s); gate now: {result}", at=at)
    return {"applied": applied, "gate": result}


def record_rotation(cur, actor: str, tool_id: str, at: datetime | None = None) -> dict[str, Any]:
    from src.app.gate import rules
    at = at or audit.now()
    if actor not in ref.IMPLEMENTERS:
        _refuse(cur, actor, tool_id, "record rotation", "The platform lead records credential rotations.", status=403)
    files, ctx = scan.context(cur, tool_id)
    if any(f.rule_id == "G01" and f.outcome == "refuse" for f in rules.scan(files, ctx)):
        _refuse(cur, actor, tool_id, "record rotation",
                "The secret is still in the code. Remove it first: rotating a key that is still committed only moves the problem.")
    pending = []
    for path, content, in_head in files:
        if in_head:
            continue
        for _line, kind, value in rules.secrets_in(path, content):
            fp = rules.fingerprint(value)
            if fp not in ctx.rotated and not rules._is_test(path):
                pending.append((fp, kind))
    if not pending:
        _refuse(cur, actor, tool_id, "record rotation", "No unrotated secret in this tool's history.")
    for fp, _kind in sorted(set(pending)):
        cur.execute("INSERT INTO secret_rotation VALUES (?, ?, ?, ?)", [fp, tool_id, at, actor])
    result = scan.scan_tool(cur, tool_id, at)
    audit.record(cur, actor, "gate", tool_id, "rotation recorded", detail=f"{len(set(pending))} credential(s); gate now: {result}", at=at)
    return {"rotated": len(set(pending)), "gate": result}
