"""The gate's checks, case by case - including the ones that must not fire."""

from __future__ import annotations

import base64
import json

from src.app.gate import rules
from src.app.gate.rules import Context

PERSONAL = Context(data_classes={"personal"}, columns={"visitors": ["buyer_name", "buyer_email"], "results": ["suburb", "result"]})


def jwt(role: str) -> str:
    b = lambda o: base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip("=")  # noqa: E731
    return f"{b({'alg': 'HS256'})}.{b({'role': role})}.{'s' * 43}"


def ids(findings):
    return {(f.rule_id, f.outcome) for f in findings}


def test_service_role_jwt_refused_but_anon_jwt_is_not_a_secret():
    assert ("G01", "refuse") in ids(rules.scan([(".env", f"KEY={jwt('service_role')}\n", True)], PERSONAL))
    assert rules.scan([(".env", f"KEY={jwt('anon')}\n", True)], PERSONAL) == []


def test_reading_from_the_environment_is_fine():
    code = 'const c = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY, baseURL: "https://ai-gateway.place-tools.example/anthropic" });'
    assert rules.scan([("netlify/functions/a.js", code, True)], PERSONAL) == []


def test_key_in_a_test_file_is_held_not_refused():
    out = rules.scan([("tests/a.test.js", f'const K = "sk-ant-api03-{"x" * 45}";', True)], PERSONAL)
    assert ids(out) == {("G01", "hold")}


def test_removed_key_refuses_until_rotation_recorded():
    key = "ghp_" + "A" * 36
    files = [(".env", f"GITHUB_TOKEN={key}\n", False)]
    assert ids(rules.scan(files, PERSONAL)) == {("G02", "refuse")}
    rotated = Context(data_classes={"personal"}, rotated={rules.fingerprint(key)})
    assert rules.scan(files, rotated) == []


def test_firestore_open_write_refused_open_read_of_public_data_allowed():
    open_rules = "match /visitors/{docId} {\n allow read, write: if true;\n }"
    public_read = "match /results/{docId} {\n allow read: if true;\n allow write: if request.auth != null;\n }"
    assert ("G04", "refuse") in ids(rules.scan([("firestore.rules", open_rules, True)], PERSONAL))
    assert rules.scan([("firestore.rules", public_read, True)], PERSONAL) == []


def test_a_later_migration_supersedes_an_open_one():
    first = "create table visitors (id int, buyer_name text);\nalter table visitors disable row level security;\ngrant select on visitors to anon;"
    later = "revoke all on visitors from anon;\nalter table visitors enable row level security;"
    files = [("supabase/migrations/0001_init.sql", first, True)]
    assert ("G04", "refuse") in ids(rules.scan(files, PERSONAL))
    assert rules.scan(files + [("supabase/migrations/0002_rls.sql", later, True)], PERSONAL) == []


def test_sql_from_input_refused_query_builder_fine():
    bad = "const sql = `select * from t where a = '${event.queryStringParameters.q}'`;"
    good = 'const { data } = await db.from("t").select("*").eq("a", event.queryStringParameters.q);'
    assert ("G05", "refuse") in ids(rules.scan([("netlify/functions/f.js", bad, True)], PERSONAL))
    assert not any(f.rule_id == "G05" for f in rules.scan([("netlify/functions/f.js", good, True)], PERSONAL))


def test_function_without_caller_check_refused_with_personal_data_held_without():
    code = 'export async function handler(event) { const { data } = await db.from("t").select("*"); return data; }'
    assert ids(rules.scan([("netlify/functions/f.js", code, True)], PERSONAL)) == {("G06", "refuse")}
    assert ids(rules.scan([("netlify/functions/f.js", code, True)], Context(data_classes={"public"}))) == {("G06", "hold")}


def test_model_call_refused_with_personal_fields_held_without():
    personal = 'import Anthropic from "@anthropic-ai/sdk";\nconst p = `Write to ${visit.buyer_name}`;'
    public = 'import Anthropic from "@anthropic-ai/sdk";\nconst p = `Describe ${listing.features}`;'
    assert ids(rules.scan([("functions/a.js", personal, True)], PERSONAL)) == {("G07", "refuse")}
    assert ids(rules.scan([("functions/a.js", public, True)], PERSONAL)) == {("G07", "hold")}


def test_made_up_package_refused_and_advisories_by_version():
    pkg = json.dumps({"dependencies": {"react": "^18.3.1", "react-suburb-maps": "^0.4.2", "markdown-it-lite": "^4.1.0"}})
    out = ids(rules.scan([("package.json", pkg, True)], PERSONAL))
    assert ("G08", "refuse") in out and ("G09", "hold") in out
    fixed = json.dumps({"dependencies": {"react": "^18.3.1", "markdown-it-lite": "^4.3.1"}})
    assert rules.scan([("package.json", fixed, True)], PERSONAL) == []


def test_agent_personal_connector():
    assert ids(rules.scan([], Context(connectors=["SharePoint", "Dropbox (personal)"]))) == {("G11", "refuse")}
    assert rules.scan([], Context(connectors=["SharePoint", "Office 365 Outlook"])) == []


def test_outcome_order():
    assert rules.outcome([]) == "pass"
    hold = rules.Finding("G10", "hold", "a", 1, "", "")
    refuse = rules.Finding("G01", "refuse", "a", 1, "", "")
    assert rules.outcome([hold]) == "hold" and rules.outcome([hold, refuse]) == "refuse"


def test_try_endpoint_stores_nothing(client):
    before = client.get("/api/audit").json()
    r = client.post("/api/gate/try", json={"content": f'const k = "sk-proj-{"a" * 45}";', "path": "src/a.js"})
    assert r.json()["outcome"] == "refuse"
    assert client.get("/api/audit").json() == before


def test_file_view_masks_keys(client):
    tid = [t for t in client.get("/api/register").json()["tools"] if t["name"] == "Trust receipt matcher"][0]["tool_id"]
    body = client.get(f"/api/gate/{tid}/file", params={"path": "config.py"}).json()["content"]
    assert "Tr0ub4dor-" in body and "..." in body


def test_identifier_named_like_a_token_is_not_a_secret():
    assert rules.scan([("src/config.js", 'const TOKEN_KEY = "place_demo_write_token";', True)], PERSONAL) == []
    # Assembled at run time so secret scanners on the repository do not
    # mistake the test's fake value for a real one.
    fake = "DB_" + "PASS" + "WORD = " + '"' + "Tr0ub4dor" + "-x9" + '"'
    assert ("G01", "refuse") in ids(rules.scan([("config.py", fake, True)], PERSONAL))
