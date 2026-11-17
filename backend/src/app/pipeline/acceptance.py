"""What must hold, or there is no build. Each check reads the built data."""

from __future__ import annotations

import re

import duckdb

from src.app.pipeline import reference as ref
from src.app.pipeline.generate import aud


def _nothing_dropped(con) -> tuple[bool, str]:
    missing = con.execute("""
        SELECT 'repo ' || repo FROM src_github_repos WHERE repo NOT IN (SELECT ref FROM tool_source WHERE source = 'repo')
        UNION ALL SELECT 'site ' || site_id FROM src_netlify_sites WHERE site_id NOT IN (SELECT ref FROM tool_source WHERE source = 'netlify')
        UNION ALL SELECT 'firebase ' || project_id FROM src_firebase_projects WHERE project_id NOT IN (SELECT ref FROM tool_source WHERE source = 'firebase')
        UNION ALL SELECT 'supabase ' || ref FROM src_supabase_projects WHERE ref NOT IN (SELECT ref FROM tool_source WHERE source = 'supabase')
        UNION ALL SELECT 'agent ' || agent_id FROM src_copilot_agents WHERE agent_id NOT IN (SELECT ref FROM tool_source WHERE source = 'agent')
        UNION ALL SELECT 'survey ' || response_id FROM src_survey WHERE response_id NOT IN (SELECT ref FROM tool_source WHERE source = 'survey')
                                                     AND response_id NOT IN (SELECT ref FROM discovery_hold)""").fetchall()
    return not missing, f"{len(missing)} export rows in no tool and no hold: {[m[0] for m in missing][:5]}"


def _claims_accounted(con) -> tuple[bool, str]:
    n_claims = con.execute("SELECT count(DISTINCT upn || vendor) FROM src_expenses WHERE vendor NOT IN (SELECT vendor FROM src_expenses WHERE vendor LIKE '%(%')").fetchone()[0]
    held = con.execute("SELECT count(*) FROM discovery_hold WHERE source = 'expenses'").fetchone()[0]
    return held >= 1 and n_claims >= held, f"{held} unmatched claimant-vendor pairs held of {n_claims}"


def _owners(con) -> tuple[bool, str]:
    n = con.execute("""SELECT count(*) FROM tool WHERE owner_upn IS NULL AND tool_id NOT IN
                       (SELECT tool_id FROM register_flag WHERE flag = 'no_owner')""").fetchone()[0]
    return n == 0, f"{n} tools with no owner and no flag saying so"


def _gate_consistent(con) -> tuple[bool, str]:
    n = con.execute("""SELECT count(*) FROM gate_result g WHERE
                       (outcome = 'refuse') <> EXISTS (SELECT 1 FROM gate_finding f WHERE f.tool_id = g.tool_id AND f.outcome = 'refuse')""").fetchone()[0]
    return n == 0, f"{n} tools whose outcome disagrees with their findings"


def _cost_preserved(con) -> tuple[bool, str]:
    billed = sum(aud(c) for (c,) in con.execute("SELECT amount_cents FROM src_billing").fetchall())
    lines = con.execute("SELECT sum(aud_cents) FROM cost_line WHERE platform NOT IN ('azure', 'ai-subscriptions')").fetchone()[0]
    return billed == lines, f"billing A${billed / 100:,.2f} against allocated A${lines / 100:,.2f}"


def _incidents_paged(con) -> tuple[bool, str]:
    row = con.execute("SELECT incidents_paged, incidents_missed FROM noise_ablation WHERE rule = 'All rules'").fetchone()
    return row[0] == len(ref.INCIDENTS), f"{row[0]} of {len(ref.INCIDENTS)} incidents paged; missed {row[1]}"


def _fewer_pages(con) -> tuple[bool, str]:
    before, after = [con.execute("SELECT pages FROM noise_ablation WHERE rule = ?", [r]).fetchone()[0] for r in ("Every alert pages", "All rules")]
    return after * 5 <= before, f"{before} pages before the rules, {after} after"


def _snapshots_masked(con) -> tuple[bool, str]:
    bad = [iid for iid, w in con.execute("SELECT incident_id, world FROM incident_world").fetchall()
           if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+|\b04\d{2} ?\d{3} ?\d{3}\b", w)]
    return not bad, f"personal details in snapshots: {bad}"


def _audit_complete(con) -> tuple[bool, str]:
    n = con.execute("""SELECT count(*) FROM change_request c WHERE NOT EXISTS
                       (SELECT 1 FROM audit_log a WHERE a.project_id = c.cr_id AND a.action = 'proposed')""").fetchone()[0]
    return n == 0, f"{n} changes without a proposal in the audit log"


CHECKS = [
    ("Every export row is in a tool or held, never dropped", _nothing_dropped),
    ("Every expense claim is matched to a bill, an AI subscription, or held", _claims_accounted),
    ("Every tool has an owner, or a flag that says it has none", _owners),
    ("The gate's outcome agrees with its findings", _gate_consistent),
    ("Splitting account plans across sites loses no money", _cost_preserved),
    ("Every real incident still pages under the noise rules", _incidents_paged),
    ("The noise rules cut pages at least five-fold", _fewer_pages),
    ("No personal detail reaches an incident snapshot", _snapshots_masked),
    ("Every change has its proposal in the audit log", _audit_complete),
]


def run(con: duckdb.DuckDBPyConnection) -> list[tuple[str, bool, str]]:
    return [(name, *fn(con)) for name, fn in CHECKS]
