"""Every defect the generator seeds is found from the data - the exports and
the code - never from the reference. And nothing clean is flagged."""

from __future__ import annotations

import pytest

from src.app.pipeline import reference as ref
from tests.conftest import tool_id

RULE_FOR = {
    "secret_in_repo": ("G01", "refuse"),
    "service_key_in_client": ("G03", "refuse"),
    "open_data_rules": ("G04", "refuse"),
    "sql_from_input": ("G05", "refuse"),
    "unauthenticated_function": ("G06", "refuse"),
    "personal_data_to_unapproved_ai": ("G07", "refuse"),
    "model_call_outside_gateway_public_data": ("G07", "hold"),
    "nonexistent_package": ("G08", "refuse"),
    "personal_data_in_logs": ("G10", "hold"),
    "key_shaped_test_fixture": ("G01", "hold"),
    "secret_in_history_only": ("G02", "refuse"),
    "agent_personal_connector": ("G11", "refuse"),
}


def findings(con, tid):
    return set(con.execute("SELECT rule_id, outcome FROM gate_finding WHERE tool_id = ?", [tid]).fetchall())


@pytest.mark.parametrize("defect", sorted(RULE_FOR))
def test_each_seeded_code_defect_is_found(built, defect):
    rule, outcome = RULE_FOR[defect]
    for key in ref.SEEDED[defect]:
        assert (rule, outcome) in findings(built, tool_id(built, key)), f"{defect} not found in {key}"


def test_each_seeded_code_defect_is_found_only_where_seeded(built):
    for defect, (rule, outcome) in RULE_FOR.items():
        if defect == "secret_in_repo":
            continue  # G01 refuse is shared with nothing else
        seeded = {tool_id(built, k) for d, (r, o) in RULE_FOR.items() if (r, o) == (rule, outcome) for k in ref.SEEDED[d]}
        found = {r[0] for r in built.execute("SELECT DISTINCT tool_id FROM gate_finding WHERE rule_id = ? AND outcome = ?", [rule, outcome]).fetchall()}
        assert found == seeded, f"{rule}/{outcome}: found {found - seeded} not seeded, missed {seeded - found}"


def test_vulnerable_dependencies_by_severity(built):
    rows = {r[0]: r[1] for r in built.execute("SELECT tool_id, outcome FROM gate_finding WHERE rule_id = 'G09'").fetchall()}
    assert set(rows) == {tool_id(built, k) for k in ref.SEEDED["vulnerable_dependency"]}
    assert rows[tool_id(built, "commission-calc")] == "refuse"  # critical advisory
    assert rows[tool_id(built, "cma-helper")] == "hold"


def test_open_read_on_public_data_is_not_a_finding(built):
    for key in ref.SEEDED["open_rules_public_data"]:
        assert ("G04", "refuse") not in findings(built, tool_id(built, key))


def test_tools_with_nothing_seeded_pass(built):
    seeded = {k for d, keys in ref.SEEDED.items() if d in RULE_FOR or d == "vulnerable_dependency" for k in keys}
    for t in ref.TOOLS:
        if t["key"] not in seeded:
            outcome = built.execute("SELECT outcome FROM gate_result WHERE tool_id = ?", [tool_id(built, t["key"])]).fetchone()[0]
            assert outcome == "pass", t["key"]


def test_orphaned_tools_found_from_the_hr_feed(built):
    found = {r[0] for r in built.execute("SELECT tool_id FROM register_flag WHERE flag = 'orphaned'").fetchall()}
    assert found == {tool_id(built, k) for k in ref.SEEDED["orphaned"]}


def test_undeclared_tools(built):
    found = {r[0] for r in built.execute("SELECT tool_id FROM tool WHERE NOT declared").fetchall()}
    assert found == {tool_id(built, k) for k in ref.UNDECLARED}


def test_duplicates_from_the_survey_process(built):
    flagged = {r[0] for r in built.execute("SELECT tool_id FROM register_flag WHERE flag = 'duplicate_process'").fetchall()}
    assert flagged == {tool_id(built, k) for pair in ref.SEEDED["duplicate_pairs"] for k in pair}


def test_renamed_sites_joined_by_key(built):
    for key in ref.SEEDED["renamed_site"]:
        t = next(t for t in ref.TOOLS if t["key"] == key)
        row = built.execute("SELECT repo, site FROM tool WHERE tool_id = ?", [tool_id(built, key)]).fetchone()
        assert row == (t["repo"], t["site"])


def test_two_repositories_one_site_is_held_not_guessed(built):
    repo, site = ref.HELD["two_repos_one_site"][0]
    hold = built.execute("SELECT ref FROM discovery_hold WHERE source = 'github'").fetchone()[0]
    assert repo in hold
    row = built.execute("SELECT repo, repo_candidates FROM tool WHERE site = ?", [site]).fetchone()
    assert row[0] is None and repo in row[1]


def test_expenses_without_a_resource_are_held(built):
    held = {r[0] for r in built.execute("SELECT ref FROM discovery_hold WHERE source = 'expenses'").fetchall()}
    assert held == {f"{u}@{ref.STAFF_DOMAIN}: {v}" for u, v in ref.HELD["expense_without_resource"]}


def test_dangling_dns(built):
    details = " ".join(r[0] for r in built.execute("SELECT detail FROM register_flag WHERE flag = 'dangling_dns'").fetchall())
    for name, target in ref.DANGLING_DNS:
        assert target in details


def test_cost_findings(built):
    kinds = {}
    for kind, tid, res in built.execute("SELECT kind, tool_id, resource FROM cost_finding").fetchall():
        kinds.setdefault(kind, set()).add(tid or res)
    assert kinds["idle"] == {tool_id(built, k) for k in ref.SEEDED["idle"]}
    assert kinds["oversized"] == {tool_id(built, k) for k in ref.SEEDED["oversized_plan"]}
    assert kinds["drift"] == {n for n, _, _ in ref.AZURE_UNDECLARED}
    assert tool_id(built, "appraisal-writer") in kinds["runaway"]


def test_tier_one_for_identity_documents(built):
    assert built.execute("SELECT tier FROM tool WHERE tool_id = ?", [tool_id(built, "rental-applications")]).fetchone()[0] == 1
