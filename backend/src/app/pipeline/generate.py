"""Generate the raw exports the inventory starts from.

Deterministic: one seed, integer draws only, so the output is byte-identical
on any machine (the build checks it against pinned digests). What it writes
is what each source would hand over - the HR feed, the inventory survey,
the GitHub, Netlify, Firebase, Supabase and Copilot Studio exports, DNS,
platform billing, expense claims and the Azure sandbox - with nothing joined
up. Joining them is the pipeline's job.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date, datetime, timedelta

import duckdb

from src.app.pipeline import code
from src.app.pipeline import reference as ref

LEAVERS = {u for u, s in ref.STAFF.items() if s[3]}
PRO_NETLIFY = {"noah.b", "leo.h", "ella.r", "hugo.n", "ben.y"}
SUPA_PRO = {"appraisal-writer", "arrears", "vendor-report", "key-register", "staff-roster", "settlement-tracker", "bond-tracker", "my-first-app"}
FIREBASE_USD = {"open-home": 2140, "entry-photos": 3890, "rental-applications": 1210, "referrals": 420, "appraisal-gen": 160,
                "auction-results": 90, "lease-renewal": 60, "vacate-checklist": 40, "arrears-dashboard": 30}
ANTHROPIC_USD = {"noah.b": 4200, "ella.r": 2600, "hugo.n": 900, "theo.v": 700, "zoe.m": 1300}
OPENAI_USD = {"leo.h": 1100}
CLAUDE_PRO = ["noah.b", "ella.r", "ben.y", "ruby.s", "isla.c"]
CHATGPT_PLUS = ["leo.h", "jack.t", "zoe.m", "theo.v"]
PUBLIC_REPOS = {"appraisal-writer", "suburb-report", "signature-gen", "cma-helper", "my-first-app"}


def account(upn: str) -> str:
    """Leavers signed up with their work address; everyone else used a personal one."""
    if upn in LEAVERS:
        return f"{upn}@{ref.STAFF_DOMAIN}"
    return f"{upn.replace('.', '')}.dev@mail.example"


def login(t: dict) -> str:
    return t["repo"].split("/")[0]


def aud(usd_cents: int) -> int:
    return (usd_cents * ref.AUD_PER_USD_BP + 5_000) // 10_000


def claimed(usd_cents: int) -> int:
    """What lands on an expense claim: converted, plus a 3% card fee."""
    return (aud(usd_cents) * 103 + 50) // 100


def month_end(m: str) -> date:
    y, mo = int(m[:4]), int(m[5:])
    nxt = date(y + (mo == 12), mo % 12 + 1, 1)
    return nxt - timedelta(days=1)


def _ins(con: duckdb.DuckDBPyConnection, table: str, rows: list[tuple]) -> None:
    if rows:
        con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(rows[0]))})", rows)


def _uuid(rng: random.Random) -> str:
    h = "".join("0123456789abcdef"[rng.randrange(16)] for _ in range(32))
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _sha(rng: random.Random) -> str:
    return "".join("0123456789abcdef"[rng.randrange(16)] for _ in range(7))


def generate(con: duckdb.DuckDBPyConnection) -> dict:
    rng = random.Random(ref.SEED)
    tools = {t["key"]: t for t in ref.TOOLS}
    out: dict = {}

    # ---- HR feed (from the managed service provider) ---------------------
    staff = []
    for upn, (name, role, office, left) in ref.STAFF.items():
        staff.append((f"{upn}@{ref.STAFF_DOMAIN}", name, role, office, "left" if left else "active", left))
    roles = ["Sales associate", "Property manager", "Leasing consultant", "Sales agent", "Administration", "Receptionist"]
    for i in range(ref.STAFF_TOTAL - len(ref.STAFF)):
        left = date(2026, 1 + rng.randrange(10), 1 + rng.randrange(28)) if rng.randrange(100) < 9 else None
        staff.append((f"s{i + 1:04d}@{ref.STAFF_DOMAIN}", f"Staff {i + 1:04d}", roles[rng.randrange(len(roles))],
                      ref.OFFICES[rng.randrange(26)], "left" if left else "active", left))
    _ins(con, "src_staff", staff)

    # ---- Inventory survey and declared accounts ---------------------------
    survey, identity, seen = [], [], set()
    for n, t in enumerate(ref.TOOLS, start=1):
        if t["key"] in ref.UNDECLARED:
            continue
        upn = t["owner"]
        url = repo = agent = None
        if t["kind"] == "agent":
            agent = t["agent_id"]
        elif t.get("dns"):
            url = f"https://{t['dns']}.{ref.DOMAIN}"
        else:
            repo = f"https://github.com/{t['repo']}"
        estimate = max(0, (t["users"] + 4) // 5 * 5 + (5 if t["users"] > 40 else 0))
        survey.append((f"R-{n:03d}", f"{upn}@{ref.STAFF_DOMAIN}", t["name"], ref.PROCESS[t["key"]], t["purpose"], repo, url, agent,
                       estimate, datetime(2026, 10, 27, 9, 0) + timedelta(minutes=37 * n)))
        if upn not in seen:
            seen.add(upn)
            if t.get("repo"):
                identity.append((f"{upn}@{ref.STAFF_DOMAIN}", "github", login(t)))
            identity.append((f"{upn}@{ref.STAFF_DOMAIN}", "email", account(upn)))
    # A builder who declared two tools under two GitHub logins.
    identity.append(("ella.r@staff.example", "github", "ellar-place"))
    _ins(con, "src_survey", survey)
    _ins(con, "src_identity", sorted(set(identity)))

    # ---- GitHub, and the code in each repository ---------------------------
    repos, files, fixes, secrets = [], [], [], {}
    site_ids = {}
    for t in ref.TOOLS:
        if t.get("hosting") == "netlify":
            site_ids[t["key"]] = _uuid(rng)
    for t in ref.TOOLS:
        if not t.get("repo"):
            continue
        created = datetime(2025, 6, 1) + timedelta(days=rng.randrange(420))
        pushed = datetime(2026, 11, 14) - timedelta(days=rng.randrange(60) if t["users"] else 200 + rng.randrange(100), hours=rng.randrange(20))
        repos.append((t["repo"], login(t), "User", "public" if t["key"] in PUBLIC_REPOS else "private",
                      "Python" if t["kind"] == "script" else "JavaScript", created, pushed))
        fs, fx, sc = code.files_for(t, rng)
        commit = _sha(rng)
        for path, content, head in fs:
            content = content.replace("{site_id:vendor-report}", site_ids.get("vendor-report", ""))
            files.append((t["repo"], path, content, head, commit if head else _sha(rng), pushed if head else created + timedelta(days=3)))
        for path, content, note in fx:
            fixes.append((t["repo"], path, content, note))
        for value, kind in sc.items():
            secrets[hashlib.sha256(value.encode()).hexdigest()[:12]] = (t["key"], kind)
    # An older copy of the vendor report, deployed to the same site by CLI.
    old = "leoh/vendor-report-old"
    repos.append((old, "leoh", "User", "private", "JavaScript", datetime(2025, 9, 2), datetime(2026, 7, 30, 16, 5)))
    for path, content in [("README.md", "# vendor-report (old)\n\nFirst version. Deploy with `netlify deploy --prod`.\n"),
                          (".netlify/state.json", json.dumps({"siteId": site_ids["vendor-report"]}) + "\n"),
                          ("package.json", json.dumps({"name": "vendor-report", "private": True, "dependencies": {"react": "^18.3.1"}}, indent=2) + "\n")]:
        files.append((old, path, content, True, "a41c0de", datetime(2026, 7, 30, 16, 5)))
    _ins(con, "src_github_repos", repos)
    _ins(con, "src_repo_files", files)
    _ins(con, "repo_fix", fixes)
    out["secrets"] = secrets

    # ---- Hosting and database exports --------------------------------------
    netlify, firebase, supabase, agents, dns = [], [], [], [], []
    for t in ref.TOOLS:
        k, users = t["key"], t["users"]
        requests = users * (30 + rng.randrange(90)) if users else 0
        if t.get("hosting") == "netlify":
            repo_url = None if k == "vendor-report" else f"https://github.com/{t['repo']}"
            netlify.append((site_ids[k], t["site"], account(t["owner"]), repo_url,
                            f"{t['dns']}.{ref.DOMAIN}" if t.get("dns") else None,
                            "pro" if t["owner"] in PRO_NETLIFY else "starter", users, requests,
                            datetime(2026, 11, 14, 18) - timedelta(days=rng.randrange(40) if users else 300)))
            if t.get("dns"):
                dns.append((f"{t['dns']}.{ref.DOMAIN}", "CNAME", f"{t['site']}.netlify.app"))
        if t.get("hosting") == "firebase":
            cols = [{"name": n, "fields": c, "docs": r} for n, c, r in t["tables"]]
            firebase.append((t["project"], account(t["owner"]), "blaze", f"https://{t['project']}.web.app", json.dumps(cols),
                             users, requests))
            if t.get("dns"):
                dns.append((f"{t['dns']}.{ref.DOMAIN}", "CNAME", f"{t['project']}.web.app"))
        if t.get("database") == "supabase":
            open_rls = k in ref.SEEDED["open_data_rules"]
            tabs = [{"name": n, "columns": c, "rows": r, "rls_enabled": not open_rls} for n, c, r in t["tables"]]
            size = 40 + sum(r for _, _, r in t["tables"]) // 30
            if k == "leaderboard":
                size = 318
            if k == "call-list":
                size = 431
            supabase.append((t["ref"], t["repo"].split("/")[1], account(t["owner"]), "pro" if k in SUPA_PRO else "free", size,
                             json.dumps(tabs), users, requests))
        if t["kind"] == "agent":
            agents.append((t["agent_id"], t["name"], "Default (tenant)", f"{t['owner']}@{ref.STAFF_DOMAIN}", json.dumps(t["connectors"]),
                           json.dumps(["SharePoint: Policies"] if k == "policy-agent" else []), users,
                           datetime(2026, 11, 3, 10) - timedelta(days=rng.randrange(90))))
    for name, target in ref.DANGLING_DNS:
        dns.append((f"{name}.{ref.DOMAIN}", "CNAME", target))
    dns += [(f"{ref.DOMAIN}", "A", "203.0.113.10"), (f"www.{ref.DOMAIN}", "CNAME", f"{ref.DOMAIN}"), (f"{ref.DOMAIN}", "MX", "mail.example")]
    _ins(con, "src_netlify_sites", netlify)
    _ins(con, "src_firebase_projects", firebase)
    _ins(con, "src_supabase_projects", supabase)
    _ins(con, "src_copilot_agents", agents)
    _ins(con, "src_dns", sorted(dns))
    out["site_ids"] = site_ids

    # ---- Billing (platform exports, US$) and expense claims (A$) -----------
    billing, expenses = [], []

    def jitter(v: int) -> int:
        return v * (92 + rng.randrange(17)) // 100

    for m in ref.BILLING_MONTHS:
        per_claim: dict[tuple[str, str], int] = {}
        for upn in sorted(PRO_NETLIFY):
            billing.append((m, "netlify", account(upn), "team:pro", "USD", 1900))
            per_claim[(upn, "Netlify")] = per_claim.get((upn, "Netlify"), 0) + 1900
        for t in ref.TOOLS:
            if t["key"] in SUPA_PRO:
                billing.append((m, "supabase", account(t["owner"]), t["ref"], "USD", 3500))
                per_claim[(t["owner"], "Supabase")] = per_claim.get((t["owner"], "Supabase"), 0) + 3500
            if t["key"] in FIREBASE_USD:
                v = jitter(FIREBASE_USD[t["key"]])
                billing.append((m, "firebase", account(t["owner"]), t["project"], "USD", v))
                per_claim[(t["owner"], "Google Cloud")] = per_claim.get((t["owner"], "Google Cloud"), 0) + v
        for upn, usd in ANTHROPIC_USD.items():
            v = jitter(usd)
            if upn == "noah.b" and m == "2026-10":
                v = 38_640  # a function retrying in a loop for a weekend: INC-07
            billing.append((m, "anthropic", account(upn), "api", "USD", v))
            per_claim[(upn, "Anthropic")] = per_claim.get((upn, "Anthropic"), 0) + v
        for upn, usd in OPENAI_USD.items():
            v = jitter(usd)
            billing.append((m, "openai", account(upn), "api", "USD", v))
            per_claim[(upn, "OpenAI")] = per_claim.get((upn, "OpenAI"), 0) + v
        n = 0
        for (upn, vendor), usd in sorted(per_claim.items()):
            left = ref.STAFF[upn][3]
            if left and month_end(m) > left:
                continue  # nobody claims after they have left; the bill keeps coming
            n += 1
            expenses.append((f"EXP-{m.replace('-', '')}-{n:03d}", f"{upn}@{ref.STAFF_DOMAIN}", m, vendor,
                             f"{vendor} - tools", claimed(usd)))
        for upn in CLAUDE_PRO:
            n += 1
            expenses.append((f"EXP-{m.replace('-', '')}-{n:03d}", f"{upn}@{ref.STAFF_DOMAIN}", m, "Anthropic (Claude Pro)", "Claude subscription", claimed(2000)))
        for upn in CHATGPT_PLUS:
            n += 1
            expenses.append((f"EXP-{m.replace('-', '')}-{n:03d}", f"{upn}@{ref.STAFF_DOMAIN}", m, "OpenAI (ChatGPT Plus)", "ChatGPT subscription", claimed(2000)))
        if m >= "2026-09":
            for upn, vendor in ref.HELD["expense_without_resource"]:
                n += 1
                expenses.append((f"EXP-{m.replace('-', '')}-{n:03d}", f"{upn}@{ref.STAFF_DOMAIN}", m, vendor, f"{vendor} app builder", claimed(3200)))
    _ins(con, "src_billing", billing)
    _ins(con, "src_expenses", expenses)

    # ---- Azure sandbox ---------------------------------------------------------
    az = [("rg-place-sandbox", "Resource group", 0), ("cae-place-sandbox", "Container Apps environment", 1_180),
          ("log-place-sandbox", "Log Analytics workspace", 310), ("st-place-sandbox-tfstate", "Storage account", 140)]
    az += list(ref.AZURE_UNDECLARED)
    _ins(con, "src_azure_resources", az)
    _ins(con, "src_tf_state", [(n,) for n in ref.AZURE_DECLARED])

    # ---- Database growth and certificates (for the forecasts) ----------------
    growth = []
    for t in ref.TOOLS:
        if t.get("database") != "supabase":
            continue
        limit = 8_000 if t["key"] in SUPA_PRO else 500
        end = next(r[4] for r in supabase if r[0] == t["ref"])
        for d in range(60):
            day = ref.DEMO_TODAY - timedelta(days=59 - d)
            if t["key"] == "leaderboard":
                # Hit the free plan's limit on 01/11 (INC-04), then old months were archived.
                hit = (date(2026, 11, 1) - day).days
                size = 500 - hit * 3 if hit >= 0 else 300 + (-hit) * 1
            elif t["key"] == "call-list":
                size = end - (59 - d) * 21 // 10
            else:
                size = max(8, end - (59 - d) * (1 + rng.randrange(2)) // 3)
            growth.append((t["ref"], day, min(size, limit), limit))
    _ins(con, "src_db_growth", growth)
    certs = []
    for t in ref.TOOLS:
        if t.get("dns"):
            host = f"{t['dns']}.{ref.DOMAIN}"
            if t["key"] == "suburb-report":
                certs.append((host, date(2026, 11, 8), False))
            elif t["key"] == "open-home":
                certs.append((host, date(2026, 11, 28), False))
            else:
                certs.append((host, ref.DEMO_TODAY + timedelta(days=40 + rng.randrange(40)), True))
    _ins(con, "src_cert", certs)
    return out
