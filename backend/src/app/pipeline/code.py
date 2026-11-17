"""The code in each tool's repository, as the GitHub export would give it.

Small but real: a package.json, a client, a serverless function, database
rules or a migration. Seeded defects are written into the files the way a
pilot tool tends to carry them - a key pasted in to get it working, a rule
opened during testing and never closed. For each, the fix branch the owner
would push is generated too; applying it is a governed write, and the gate
re-scans the code rather than trusting a flag.

Every key here is synthetic: random characters in the shape of a real one.
"""

from __future__ import annotations

import base64
import json
import random

from src.app.pipeline import reference as ref


def _rand(rng: random.Random, n: int, alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789") -> str:
    return "".join(alphabet[rng.randrange(len(alphabet))] for _ in range(n))


def _jwt(rng: random.Random, ref_id: str, role: str) -> str:
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256', 'typ': 'JWT'})}.{b64({'iss': 'supabase', 'ref': ref_id, 'role': role, 'iat': 1767225600})}.{_rand(rng, 43)}"


def anthropic_key(rng: random.Random) -> str:
    return "sk-ant-api03-" + _rand(rng, 48, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def openai_key(rng: random.Random) -> str:
    return "sk-proj-" + _rand(rng, 48)


def github_token(rng: random.Random) -> str:
    return "ghp_" + _rand(rng, 36)


SEEDED = ref.SEEDED


def has(defect: str, key: str) -> bool:
    return key in SEEDED.get(defect, [])


VERSIONS = {"react": "18.3.1", "react-dom": "18.3.1", "vite": "5.4.10", "@supabase/supabase-js": "2.45.4", "firebase": "10.14.1",
            "@anthropic-ai/sdk": "0.32.1", "openai": "4.71.0", "date-fns": "3.6.0", "@netlify/functions": "2.8.2",
            "markdown-it-lite": "4.3.1", "jsonwebtoken-mini": "2.1.0", "csv-quickparse": "1.9.2", "papaparse": "5.4.1",
            "leaflet": "1.9.4", "pdf-lib": "1.17.1", "zod": "3.23.8", "dayjs": "1.11.13"}


def _package_json(t: dict) -> str:
    deps = ["react", "react-dom", "date-fns"]
    if t.get("database") == "supabase":
        deps.append("@supabase/supabase-js")
    if t.get("hosting") == "firebase" or t.get("database") == "firestore":
        deps.append("firebase")
    if t.get("hosting") == "netlify":
        deps.append("@netlify/functions")
    if t.get("ai") == "anthropic_api":
        deps.append("@anthropic-ai/sdk")
    if t.get("ai") == "openai_personal":
        deps.append("openai")
    extra = {"commission-calc": "jsonwebtoken-mini", "cma-helper": "markdown-it-lite", "route-planner": "csv-quickparse",
             "brochure-helper": "pdf-lib", "suburb-report": "papaparse"}
    if t["key"] in extra:
        deps.append(extra[t["key"]])
    versions = dict(VERSIONS)
    # Under the synthetic advisories.
    if has("vulnerable_dependency", t["key"]):
        versions.update({"jsonwebtoken-mini": "2.0.1", "markdown-it-lite": "4.1.0", "csv-quickparse": "1.7.2"})
    out = {d: f"^{versions[d]}" for d in deps}
    # Names a model suggested that no registry has ever published.
    if t["key"] == "listing-copy" and has("nonexistent_package", "listing-copy"):
        out["anthropic-listing-helper"] = "^1.2.0"
    if t["key"] == "suburb-report" and has("nonexistent_package", "suburb-report"):
        out["react-suburb-maps"] = "^0.4.2"
    return json.dumps({"name": t["repo"].split("/")[1], "private": True, "type": "module",
                       "scripts": {"dev": "vite", "build": "vite build"}, "dependencies": out}, indent=2) + "\n"


def _fixed_package_json(t: dict) -> str:
    text = json.loads(_package_json(t))
    deps = text["dependencies"]
    deps.pop("anthropic-listing-helper", None)
    deps.pop("react-suburb-maps", None)
    for d in ("jsonwebtoken-mini", "markdown-it-lite", "csv-quickparse"):
        if d in deps:
            deps[d] = f"^{VERSIONS[d]}"
    return json.dumps(text, indent=2) + "\n"


def _personal_cols(t: dict) -> list[str]:
    cols = [c for _, columns, _ in t.get("tables", []) for c in columns]
    return [c for c in cols if any(p in c for p in ("name", "email", "phone", "mobile"))]


def _supabase_client(t: dict, service_in_client: bool) -> str:
    key = "import.meta.env.VITE_SUPABASE_SERVICE_ROLE_KEY" if service_in_client else "import.meta.env.VITE_SUPABASE_ANON_KEY"
    return (f'import {{ createClient }} from "@supabase/supabase-js";\n\n'
            f'export const supabase = createClient("https://{t["ref"]}.supabase.co", {key});\n')


def _migration(t: dict, open_rls: bool) -> str:
    lines = []
    for name, cols, _ in t["tables"]:
        body = ",\n  ".join(["id bigint generated always as identity primary key"] + [f"{c} text" for c in cols])
        lines.append(f"create table {name} (\n  {body}\n);")
        if open_rls:
            lines.append(f"-- RLS off while testing the import\nalter table {name} disable row level security;")
            lines.append(f"grant select, insert, update on {name} to anon;")
        else:
            lines.append(f"alter table {name} enable row level security;")
            lines.append(f'create policy "staff only" on {name} for all to authenticated\n'
                         f"  using (auth.jwt() ->> 'email' like '%@{ref.STAFF_DOMAIN}');")
    return "\n\n".join(lines) + "\n"


def _firestore_rules(t: dict, open_rules: bool) -> str:
    blocks = []
    for name, _, _ in t["tables"]:
        if open_rules:
            body = "      allow read, write: if true;"
        elif t["key"] == "auction-results":
            body = "      allow read: if true;\n      allow write: if request.auth != null;"
        else:
            body = f"      allow read, write: if request.auth != null && request.auth.token.email.matches('.*@{ref.STAFF_DOMAIN.replace('.', '[.]')}');"
        blocks.append(f"    match /{name}/{{docId}} {{\n{body}\n    }}")
    return "rules_version = '2';\nservice cloud.firestore {\n  match /databases/{database}/documents {\n" + "\n".join(blocks) + "\n  }\n}\n"


def _storage_rules(open_rules: bool) -> str:
    rule = "allow read: if true;\n      allow write: if request.auth != null;" if open_rules else \
        f"allow read, write: if request.auth != null && request.auth.token.email.matches('.*@{ref.STAFF_DOMAIN.replace('.', '[.]')}');"
    return ("rules_version = '2';\nservice firebase.storage {\n  match /b/{bucket}/o {\n"
            f"    match /applications/{{allPaths=**}} {{\n      {rule}\n    }}\n  }}\n}}\n")


AUTH_CHECK = ('  const user = context.clientContext && context.clientContext.user;\n'
              '  if (!user || !user.email.endsWith("@' + ref.STAFF_DOMAIN + '")) {\n'
              '    return { statusCode: 401, body: "Sign in with your work account." };\n  }\n')


def _data_function(t: dict, *, unauth: bool, sql_concat: bool, log_pii: bool) -> tuple[str, str]:
    table, cols, _ = t["tables"][0]
    path = f"netlify/functions/{table}.js"
    head = ('import { createClient } from "@supabase/supabase-js";\n\n'
            f'const db = createClient("https://{t["ref"]}.supabase.co", process.env.SUPABASE_SERVICE_ROLE_KEY);\n\n'
            "export async function handler(event, context) {\n")
    auth = "" if unauth else AUTH_CHECK
    first = cols[0]
    if sql_concat:
        query = (f"  const sql = `select * from {table} where {first} = '${{event.queryStringParameters.q}}'`;\n"
                 "  const { data, error } = await db.rpc(\"exec_sql\", { sql });\n")
    else:
        query = (f'  const {{ data, error }} = await db.from("{table}").select("*")'
                 f'.eq("{first}", event.queryStringParameters.q).limit(200);\n')
    log = ""
    if log_pii:
        pii = [c for c in cols if "phone" in c or "email" in c]
        log = f'  console.log("lookup", {", ".join("data[0]." + c for c in pii)});\n'
    tail = "  if (error) return { statusCode: 500, body: error.message };\n  return { statusCode: 200, body: JSON.stringify(data) };\n}\n"
    return path, head + auth + query + log + tail


def _ai_function(t: dict, rng: random.Random, *, inline_key: str | None, gateway: bool) -> tuple[str, str]:
    personal = _personal_cols(t)
    if t["key"] == "feedback-summariser":
        obj, field = "visit", "buyer_name"
    else:
        field = personal[0] if personal else "features"
        obj = t["tables"][0][0][:-1] if t.get("tables") else "listing"
    folder = "netlify/functions" if t.get("hosting") == "netlify" else "functions"
    prompt_field = f"${{{obj}.{field}}}"
    if t["ai"] == "openai_personal":
        key = f'"{inline_key}"' if inline_key else "process.env.OPENAI_API_KEY"
        base = f', baseURL: "https://{ref.APPROVED_AI_HOSTS[0]}/openai"' if gateway else ""
        client = f'import OpenAI from "openai";\n\nconst client = new OpenAI({{ apiKey: {key}{base} }});\n\n'
        call = ('  const out = await client.chat.completions.create({\n    model: "gpt-4o-mini",\n'
                f'    messages: [{{ role: "user", content: `Summarise the feedback from {prompt_field}: ${{{obj}.feedback}}` }}],\n  }});\n')
        name = "summarise"
    else:
        key = f'"{inline_key}"' if inline_key else "process.env.ANTHROPIC_API_KEY"
        base = f', baseURL: "https://{ref.APPROVED_AI_HOSTS[0]}/anthropic"' if gateway else ""
        client = f'import Anthropic from "@anthropic-ai/sdk";\n\nconst client = new Anthropic({{ apiKey: {key}{base} }});\n\n'
        call = ('  const out = await client.messages.create({\n    model: "claude-haiku-4-5",\n    max_tokens: 800,\n'
                f'    messages: [{{ role: "user", content: `Write it for {prompt_field}. Notes: ${{{obj}.notes}}` }}],\n  }});\n')
        name = "draft"
    body = (client + "export async function handler(event, context) {\n" + AUTH_CHECK +
            f"  const {obj} = JSON.parse(event.body);\n" + call +
            "  return { statusCode: 200, body: JSON.stringify(out) };\n}\n")
    return f"{folder}/{name}.js", body


def files_for(t: dict, rng: random.Random) -> tuple[list[tuple[str, str, bool]], list[tuple[str, str, str]], dict]:
    """(files [(path, content, in_head)], fixes [(path, content or '', note)], secrets {fingerprint-source: kind})."""
    k = t["key"]
    files: list[tuple[str, str, bool]] = []
    fixes: list[tuple[str, str, str]] = []
    secrets: dict[str, str] = {}
    files.append(("README.md", f"# {t['name']}\n\n{t['purpose']}\n", True))

    if t["kind"] == "script":
        req = "requests==2.32.3\npandas==2.2.3\nopenpyxl==3.1.5\n"
        files.append(("requirements.txt", req, True))
        if has("secret_in_repo", k):
            pw = "Tr0ub4dor-" + _rand(rng, 14)
            secrets[pw] = "password"
            files.append(("config.py", f'BANK_FEED_URL = "https://bankfeed.example/api"\nBANK_FEED_USER = "trust-ops"\nBANK_FEED_PASSWORD = "{pw}"\n', True))
            fixes.append(("config.py", 'import os\n\nBANK_FEED_URL = "https://bankfeed.example/api"\nBANK_FEED_USER = "trust-ops"\n'
                                       'BANK_FEED_PASSWORD = os.environ["BANK_FEED_PASSWORD"]\n', "Read the password from the environment."))
        else:
            files.append(("config.py", 'import os\n\nSOURCE_DIR = os.environ.get("SOURCE_DIR", "./input")\n', True))
        files.append(("main.py", "from config import *\n\n\ndef main():\n    print('done')\n\n\nif __name__ == '__main__':\n    main()\n", True))
        return files, fixes, secrets

    files.append(("package.json", _package_json(t), True))
    if has("nonexistent_package", k) or has("vulnerable_dependency", k):
        fixes.append(("package.json", _fixed_package_json(t), "Remove or upgrade the flagged dependency."))
    files.append(("src/main.jsx", 'import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App.jsx";\n\n'
                                  'createRoot(document.getElementById("root")).render(<App />);\n', True))

    if t.get("hosting") == "netlify":
        files.append(("netlify.toml", '[build]\n  command = "npm run build"\n  publish = "dist"\n  functions = "netlify/functions"\n', True))

    if t.get("database") == "supabase" and t["tables"]:
        svc = has("service_key_in_client", k)
        files.append(("src/lib/supabase.js", _supabase_client(t, svc), True))
        if svc:
            fixes.append(("src/lib/supabase.js", _supabase_client(t, False), "Use the anon key in the browser; the access rules decide."))
        open_rls = has("open_data_rules", k)
        files.append(("supabase/migrations/0001_init.sql", _migration(t, open_rls), True))
        if open_rls:
            fixes.append(("supabase/migrations/0002_rls.sql",
                          "\n".join(f"revoke all on {n} from anon;\nalter table {n} enable row level security;\n"
                                    f'create policy "staff only" on {n} for all to authenticated\n'
                                    f"  using (auth.jwt() ->> 'email' like '%@{ref.STAFF_DOMAIN}');" for n, _, _ in t["tables"]) + "\n",
                          "Turn row level security on and revoke the anonymous grant."))
            # The fix supersedes the old migration rather than editing it; the
            # scanner reads the migrations in order, so the last word wins.
        if t["hosting"] == "netlify":
            unauth, sqlc, logp = has("unauthenticated_function", k), has("sql_from_input", k), has("personal_data_in_logs", k)
            path, body = _data_function(t, unauth=unauth, sql_concat=sqlc, log_pii=logp)
            files.append((path, body, True))
            if unauth or sqlc or logp:
                fixes.append((path, _data_function(t, unauth=False, sql_concat=False, log_pii=False)[1],
                              "Check the caller, parameterise the query, log no personal data."))
        if has("secret_in_repo", k):
            jwt = _jwt(rng, t["ref"], "service_role")
            secrets[jwt] = "supabase service role key"
            files.append((".env", f"VITE_SUPABASE_ANON_KEY={_jwt(rng, t['ref'], 'anon')}\nSUPABASE_SERVICE_ROLE_KEY={jwt}\n", True))
            fixes.append((".env", "", "Delete .env from the repository and add it to .gitignore."))
            fixes.append((".env.example", "VITE_SUPABASE_ANON_KEY=\nSUPABASE_SERVICE_ROLE_KEY=\n", "Document the variables without values."))

    if t.get("database") == "firestore" and t["tables"]:
        files.append((".firebaserc", json.dumps({"projects": {"default": t["project"]}}, indent=2) + "\n", True))
        files.append(("firebase.json", json.dumps({"hosting": {"public": "dist"}, "firestore": {"rules": "firestore.rules"},
                                                   "storage": {"rules": "storage.rules"}}, indent=2) + "\n", True))
        open_fs = has("open_data_rules", k) and k != "rental-applications"
        files.append(("firestore.rules", _firestore_rules(t, open_fs), True))
        if open_fs:
            fixes.append(("firestore.rules", _firestore_rules(t, False), "Staff accounts only."))
        if k == "rental-applications":
            open_st = has("open_data_rules", k)
            files.append(("storage.rules", _storage_rules(open_st), True))
            if open_st:
                fixes.append(("storage.rules", _storage_rules(False), "Staff accounts only."))
        table, cols, _ = t["tables"][0]
        logp = has("personal_data_in_logs", k)
        log = f'  console.log("new {table[:-1]}", ' + ", ".join(f"doc.{c}" for c in cols if "email" in c or "phone" in c) + ");\n" if logp else ""
        save = ('import { getFirestore, addDoc, collection } from "firebase/firestore";\n\n'
                f"export async function save(doc) {{\n{log}  return addDoc(collection(getFirestore(), \"{table}\"), doc);\n}}\n")
        files.append(("src/save.js", save, True))
        if logp:
            fixes.append(("src/save.js", save.replace(log, ""), "Log no personal data."))

    if t.get("database") == "supabase" and t["hosting"] is None:
        files.append((".env.example", "VITE_SUPABASE_URL=\nVITE_SUPABASE_ANON_KEY=\n", True))
        files.append(("src/lib/supabase.js", _supabase_client(t, False), True))

    if t.get("ai") in ("anthropic_api", "openai_personal"):
        inline = None
        if has("secret_in_repo", k):
            inline = openai_key(rng) if t["ai"] == "openai_personal" else anthropic_key(rng)
            secrets[inline] = "model API key"
        path, body = _ai_function(t, rng, inline_key=inline, gateway=False)
        files.append((path, body, True))
        fixes.append((path, _ai_function(t, rng, inline_key=None, gateway=True)[1], "Call the model through the AI gateway, key from the environment."))

    if t.get("hosting") == "netlify" and k == "vendor-report":
        files.append((".netlify/state.json", json.dumps({"siteId": "{site_id:vendor-report}"}) + "\n", True))

    if has("key_shaped_test_fixture", k):
        files.append(("tests/quote.test.js", 'import { quote } from "../src/quote.js";\n\n'
                                             f'const FAKE_KEY = "sk-ant-api03-{"EXAMPLEKEYNOTREAL" * 3}";\n\n'
                                             'test("quotes 6.5% of rent", () => {\n  expect(quote(50000, FAKE_KEY)).toBe(3250);\n});\n', True))
    if has("secret_in_history_only", k):
        tok = github_token(rng)
        secrets[tok] = "GitHub personal access token"
        files.append((".env", f"GITHUB_TOKEN={tok}\n", False))
    return files, fixes, secrets
