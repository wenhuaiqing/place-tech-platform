"""The production gate's checks.

Each check reads the code (or an agent's configuration) and returns findings.
A finding either refuses - the tool does not reach production until it is
fixed - or holds it for a person to decide. Nothing is a warning that can be
scrolled past.

The checks aim at what AI-written pilot code tends to get wrong: a key
pasted in to make it work, the database's access rules switched off during
testing, a privileged key shipped to the browser, SQL assembled from input,
a function that answers anyone, a package name the model made up, personal
data sent to a model on someone's own account.

Runnable on its own: `python -m src.app.gate.cli <path>` scans a folder, so
the same checks run in each repository's CI (see paved-road/).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field

from src.app.pipeline import reference as ref


@dataclass
class Finding:
    rule_id: str
    outcome: str  # refuse | hold
    path: str
    line: int
    evidence: str
    detail: str


@dataclass
class Context:
    """What a check may know about the tool besides its code."""
    data_classes: set[str] = field(default_factory=set)
    columns: dict[str, list[str]] = field(default_factory=dict)  # collection or table -> columns
    connectors: list[str] = field(default_factory=list)
    rotated: set[str] = field(default_factory=set)  # fingerprints of rotated secrets


RULES = {
    "G01": ("Secret in the code", "A live credential in a file that is deployed or shared."),
    "G02": ("Secret in the history, not rotated", "Removed from the code but still in the repository's history, and never rotated."),
    "G03": ("Privileged key in the browser", "A key that bypasses the database's access rules, readable by anyone who opens the site."),
    "G04": ("Data open to the internet", "Database or storage rules that let anyone read or write personal data."),
    "G05": ("SQL built from input", "A query assembled from what the caller sent: injection."),
    "G06": ("Function answers anyone", "A serverless function that returns data without checking who is asking."),
    "G07": ("Model called outside the gateway", "A model API called directly on a personal key instead of through the AI gateway."),
    "G08": ("Package that does not exist", "A dependency no registry publishes - often a name a model invented. Anyone can register it."),
    "G09": ("Dependency under an advisory", "A dependency version with a known vulnerability (synthetic advisories in this demo)."),
    "G10": ("Personal data in logs", "Personal details written to logs, which are kept longer and read more widely."),
    "G11": ("Agent connected to personal storage", "A Copilot Studio agent with a connector to a personal mailbox or drive."),
}

PERSONAL_CLASSES = {"personal", "sensitive", "financial"}

SECRET_PATTERNS = [
    ("Anthropic API key", re.compile(r"sk-ant-api03-[A-Za-z0-9_\-]{40,}")),
    ("OpenAI API key", re.compile(r"sk-proj-[A-Za-z0-9]{40,}")),
    ("GitHub token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("JSON web token", re.compile(r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")),
    ("password literal", re.compile(r"(?i)\b\w*(password|secret|api_key|token)\w*\s*=\s*[\"']([^\"'\s]{8,})[\"']")),
]
AI_SDK = re.compile(r"@anthropic-ai/sdk|from \"openai\"|api\.anthropic\.com|api\.openai\.com")


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def mask(value: str) -> str:
    return value[:10] + "..." + value[-4:] if len(value) > 18 else value[:3] + "..."


def _jwt_role(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("role")
    except Exception:  # noqa: BLE001 - not a JWT after all
        return None


def _is_test(path: str) -> bool:
    return bool(re.search(r"(^|/)(tests?|__tests__)/|\.test\.|\.spec\.", path))


def secrets_in(path: str, content: str) -> list[tuple[int, str, str]]:
    """(line, kind, value) for every credential-shaped value. An anon JWT is
    public by design and is not a secret; a service_role one is."""
    out = []
    for i, line in enumerate(content.splitlines(), start=1):
        if "process.env" in line or "os.environ" in line or "import.meta.env" in line:
            continue
        for kind, pat in SECRET_PATTERNS:
            for m in pat.finditer(line):
                value = m.group(2) if kind == "password literal" else m.group(0)
                # A credential looks random. A value of plain words - a storage
                # key's name, an env variable's name - is an identifier, not a secret.
                if kind == "password literal" and re.fullmatch(r"[A-Za-z_.:-]+", value):
                    continue
                if kind == "JSON web token":
                    role = _jwt_role(value)
                    if role != "service_role":
                        continue
                    kind = "Supabase service role key"
                out.append((i, kind, value))
    return out


def check_secrets(files: list[tuple[str, str, bool]], ctx: Context) -> list[Finding]:
    found = []
    head_values = set()
    for path, content, in_head in files:
        if not in_head:
            continue
        for line, kind, value in secrets_in(path, content):
            head_values.add(value)
            if _is_test(path):
                found.append(Finding("G01", "hold", path, line, f"{kind}: {mask(value)}",
                                     "Key-shaped string in a test file. A person confirms it is not a live key."))
            else:
                found.append(Finding("G01", "refuse", path, line, f"{kind}: {mask(value)}",
                                     f"Remove the {kind.lower()} from the code, read it from the environment, then rotate it."))
    for path, content, in_head in files:
        if in_head:
            continue
        for line, kind, value in secrets_in(path, content):
            if value in head_values or _is_test(path):
                continue
            if fingerprint(value) in ctx.rotated:
                continue
            found.append(Finding("G02", "refuse", path, line, f"{kind}: {mask(value)}",
                                 "Deleting the line does not remove it from the history. Rotate the credential, then record the rotation."))
    return found


def check_client_keys(files, ctx) -> list[Finding]:
    found = []
    for path, content, in_head in files:
        if not in_head or not path.startswith("src/"):
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if re.search(r"SERVICE_ROLE|service_role", line):
                found.append(Finding("G03", "refuse", path, i, line.strip()[:120],
                                     "The browser bundle carries a key that ignores row level security. Use the anon key; let the rules decide."))
    return found


def _final_supabase_state(files) -> dict[str, dict]:
    state: dict[str, dict] = {}
    migrations = sorted((p, c) for p, c, h in files if h and p.startswith("supabase/migrations/"))
    for path, content in migrations:
        for m in re.finditer(r"create table (\w+)", content):
            state.setdefault(m.group(1), {"rls": False, "anon": False, "path": path})
        for m in re.finditer(r"alter table (\w+) (enable|disable) row level security", content):
            state.setdefault(m.group(1), {"rls": False, "anon": False, "path": path})
            state[m.group(1)].update(rls=m.group(2) == "enable", path=path)
        for m in re.finditer(r"grant [\w, ]+ on (\w+) to anon", content):
            state.setdefault(m.group(1), {"rls": False, "anon": False, "path": path})
            state[m.group(1)].update(anon=True, path=path)
        for m in re.finditer(r"revoke all on (\w+) from anon", content):
            if m.group(1) in state:
                state[m.group(1)]["anon"] = False
    return state


def check_open_rules(files, ctx) -> list[Finding]:
    from src.app.pipeline.discover import classify_columns
    found = []
    for path, content, in_head in files:
        if not in_head:
            continue
        if path == "firestore.rules":
            for m in re.finditer(r"match /(\w+)/\{\w+\} \{([^}]*)\}", content):
                coll, body = m.group(1), m.group(2)
                classes = classify_columns(ctx.columns.get(coll, []))
                line = content[: m.start()].count("\n") + 1
                if re.search(r"allow (read, )?write: if true", body):
                    found.append(Finding("G04", "refuse", path, line, f"match /{coll}: allow write: if true",
                                         f"Anyone can write to {coll}. Require a signed-in staff account."))
                elif re.search(r"allow read(, write)?: if true", body) and classes & PERSONAL_CLASSES:
                    found.append(Finding("G04", "refuse", path, line, f"match /{coll}: allow read: if true",
                                         f"Anyone can read {coll}, which holds {', '.join(sorted(classes & PERSONAL_CLASSES))} data."))
        if path == "storage.rules" and re.search(r"allow read: if true", content) and ctx.data_classes & PERSONAL_CLASSES:
            line = content[: content.index("allow read: if true")].count("\n") + 1
            found.append(Finding("G04", "refuse", path, line, "allow read: if true",
                                 "Uploaded files are readable by anyone with the link, and this tool stores personal documents."))
    for table, st in _final_supabase_state(files).items():
        classes = classify_columns(ctx.columns.get(table, []))
        if (not st["rls"] or st["anon"]) and classes & PERSONAL_CLASSES:
            what = "row level security is off" if not st["rls"] else "the anonymous role has a grant"
            found.append(Finding("G04", "refuse", st["path"], 1, f"table {table}: {what}",
                                 f"With the public anon key, anyone can read {table} ({', '.join(sorted(classes & PERSONAL_CLASSES))} data)."))
    return found


def check_sql(files, ctx) -> list[Finding]:
    found = []
    pat = re.compile(r"(`[^`]*\b(select|insert|update|delete)\b[^`]*\$\{[^}]*(event|req|query|params)[^}]*\}[^`]*`)"
                     r"|([\"'][^\"']*\b(select|insert|update|delete)\b[^\"']*[\"']\s*\+\s*\w*(event|req|query|params))", re.I)
    for path, content, in_head in files:
        if not in_head:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if pat.search(line):
                found.append(Finding("G05", "refuse", path, i, line.strip()[:120],
                                     "The query is built from the caller's input. Use the client's query builder or a parameter."))
    return found


AUTH_TOKENS = ("clientContext", "authorization", "Authorization", "verifyIdToken", "getUser", "request.auth")


def check_functions(files, ctx) -> list[Finding]:
    found = []
    for path, content, in_head in files:
        if not in_head or not re.match(r"(netlify/)?functions/", path):
            continue
        reads_data = re.search(r"\.from\(|\.rpc\(|getFirestore|collection\(", content)
        if reads_data and not any(t in content for t in AUTH_TOKENS):
            personal = bool(ctx.data_classes & PERSONAL_CLASSES)
            found.append(Finding("G06", "refuse" if personal else "hold", path, 1, "no caller check before reading data",
                                 "Anyone with the URL gets the data. Check the signed-in user first."
                                 + (" This tool holds personal data." if personal else "")))
    return found


def check_ai(files, ctx) -> list[Finding]:
    from src.app.pipeline.discover import classify_columns
    found = []
    for path, content, in_head in files:
        if not in_head or path == "package.json" or not AI_SDK.search(content):
            continue
        if any(h in content for h in ref.APPROVED_AI_HOSTS):
            continue
        fields = re.findall(r"\$\{\w+\.(\w+)\}", content)
        personal = sorted({f for f in fields if classify_columns([f]) & PERSONAL_CLASSES})
        if personal:
            found.append(Finding("G07", "refuse", path, 1, f"prompt includes {', '.join(personal)}",
                                 "Personal information goes to a model on a personal key, with no record and no masking. Route it through the AI gateway."))
        else:
            found.append(Finding("G07", "hold", path, 1, "model called directly",
                                 "No personal data in the prompt, but the call should still go through the gateway, so it is logged and billed to Place."))
    return found


def _ver(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def check_packages(files, ctx) -> list[Finding]:
    found = []
    registry = set(ref.REGISTRY_SNAPSHOT)
    advisories = {pkg: (aid, fixed, sev, why) for aid, pkg, fixed, sev, why in ref.ADVISORIES}
    for path, content, in_head in files:
        if not in_head or path != "package.json":
            continue
        deps = json.loads(content).get("dependencies", {})
        for name, version in deps.items():
            line = next((i for i, ln in enumerate(content.splitlines(), start=1) if f'"{name}"' in ln), 1)
            if name not in registry:
                found.append(Finding("G08", "refuse", path, line, f"{name} {version}",
                                     "No registry publishes this package. If someone registers the name, the next install runs their code."))
            elif name in advisories:
                aid, fixed, sev, why = advisories[name]
                if _ver(version) < _ver(fixed):
                    found.append(Finding("G09", "refuse" if sev == "critical" else "hold", path, line, f"{name} {version} ({aid}, {sev})",
                                         f"{why} Fixed in {fixed}."))
    return found


def check_logs(files, ctx) -> list[Finding]:
    found = []
    for path, content, in_head in files:
        if not in_head:
            continue
        for i, line in enumerate(content.splitlines(), start=1):
            if re.search(r"console\.log|print\(", line) and re.search(r"email|phone|mobile|dob|licence", line):
                found.append(Finding("G10", "hold", path, i, line.strip()[:120], "Personal details in the logs. Log an id instead."))
    return found


def check_agent(ctx: Context) -> list[Finding]:
    return [Finding("G11", "refuse", "agent connectors", 1, c,
                    "Tenant data leaves the tenant for an account Place does not control. Use the Microsoft 365 connector.")
            for c in ctx.connectors if "(personal)" in c]


CHECKS = [check_secrets, check_client_keys, check_open_rules, check_sql, check_functions, check_ai, check_packages, check_logs]


def scan(files: list[tuple[str, str, bool]], ctx: Context, disabled: set[str] | None = None) -> list[Finding]:
    disabled = disabled or set()
    out: list[Finding] = []
    for check in CHECKS:
        out += check(files, ctx)
    out += check_agent(ctx)
    return [f for f in out if f.rule_id not in disabled]


def outcome(findings: list[Finding]) -> str:
    if any(f.outcome == "refuse" for f in findings):
        return "refuse"
    if findings:
        return "hold"
    return "pass"
