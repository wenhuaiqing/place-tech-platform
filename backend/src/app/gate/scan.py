"""Run the gate over every tool in the register, and price each check.

The ablation switches one check off at a time and counts what would then
reach production: tools that pass only because that check is gone, the
personal records they hold, the live credentials, the people who use them.
Exposure, not work, is the measure - and a tool another check also refuses
is counted as caught, which is the point of having more than one.
"""

from __future__ import annotations

import json
from datetime import datetime

import duckdb

from src.app.gate import rules


def context(con: duckdb.DuckDBPyConnection, tool_id: str) -> tuple[list[tuple[str, str, bool]], rules.Context]:
    t = con.execute("SELECT repo, repo_candidates, site, db_ref, agent_id, data_classes FROM tool WHERE tool_id = ?", [tool_id]).fetchone()
    repo, candidates, site, db_ref, agent_id, classes = t
    repo_list = [repo] if repo else [r.strip() for r in (candidates or "").split(",") if r.strip()]
    files = []
    for r in repo_list:
        files += [(f"{p}" if len(repo_list) == 1 else f"{r}:{p}", c, h) for p, c, h in con.execute(
            "SELECT path, content, in_head FROM src_repo_files WHERE repo = ? ORDER BY path, in_head", [r]).fetchall()]
    if len(repo_list) > 1:
        # Two candidate repositories: scan both, paths qualified. Rules match on the bare path.
        files = [(p.split(":", 1)[1], c, h) for p, c, h in files]
    columns: dict[str, list[str]] = {}
    if site:
        row = con.execute("SELECT collections FROM src_firebase_projects WHERE project_id = ?", [site]).fetchone()
        if row:
            columns |= {c["name"]: c["fields"] for c in json.loads(row[0])}
    if db_ref:
        row = con.execute("SELECT tables FROM src_supabase_projects WHERE ref = ?", [db_ref]).fetchone()
        if row:
            columns |= {c["name"]: c["columns"] for c in json.loads(row[0])}
    connectors = []
    if agent_id:
        connectors = json.loads(con.execute("SELECT connectors FROM src_copilot_agents WHERE agent_id = ?", [agent_id]).fetchone()[0])
    rotated = {r[0] for r in con.execute("SELECT fingerprint FROM secret_rotation").fetchall()}
    ctx = rules.Context(data_classes=set((classes or "").split(", ")), columns=columns, connectors=connectors, rotated=rotated)
    return files, ctx


def scan_tool(con: duckdb.DuckDBPyConnection, tool_id: str, at: datetime) -> str:
    files, ctx = context(con, tool_id)
    findings = rules.scan(files, ctx)
    con.execute("DELETE FROM gate_finding WHERE tool_id = ?", [tool_id])
    con.execute("DELETE FROM gate_result WHERE tool_id = ?", [tool_id])
    if findings:
        con.executemany("INSERT INTO gate_finding VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(tool_id, f.rule_id, f.outcome, f.path, f.line, f.evidence, f.detail) for f in findings])
    result = rules.outcome(findings)
    con.execute("INSERT INTO gate_result VALUES (?, ?, ?, ?, ?, ?)",
                [tool_id, result, sum(f.outcome == "refuse" for f in findings), sum(f.outcome == "hold" for f in findings),
                 sum(1 for _, _, h in files if h), at])
    return result


def scan_all(con: duckdb.DuckDBPyConnection, at: datetime) -> dict[str, int]:
    out = {"pass": 0, "hold": 0, "refuse": 0}
    for (tid,) in con.execute("SELECT tool_id FROM tool WHERE status NOT IN ('retired', 'merged') ORDER BY tool_id").fetchall():
        out[scan_tool(con, tid, at)] += 1
    return out


def ablation(con: duckdb.DuckDBPyConnection) -> list[tuple]:
    tools = con.execute("SELECT tool_id, name, records, users_30d, data_classes FROM tool ORDER BY tool_id").fetchall()
    scanned = {}
    for tid, *_ in tools:
        files, ctx = context(con, tid)
        scanned[tid] = (files, ctx, rules.outcome(rules.scan(files, ctx)))
    rows = []
    for rule_id in rules.RULES:
        through, records, secrets, users = [], 0, 0, 0
        for tid, name, rec, usr, classes in tools:
            files, ctx, now = scanned[tid]
            if now == "pass":
                continue
            findings = rules.scan(files, ctx, disabled={rule_id})
            if rules.outcome(findings) == "pass":
                through.append(name)
                if set((classes or "").split(", ")) & rules.PERSONAL_CLASSES:
                    records += rec
                users += usr
                if rule_id in ("G01", "G02"):
                    secrets += sum(1 for f in rules.scan(files, ctx) if f.rule_id == rule_id and f.outcome == "refuse")
        rows.append((rule_id, len(through), records, secrets, users, ", ".join(through)))
    con.execute("DELETE FROM gate_ablation")
    con.executemany("INSERT INTO gate_ablation VALUES (?, ?, ?, ?, ?, ?)", rows)
    return rows
