"""Days 1 to 30: join the exports into one register of tools.

Each export knows part of a tool - the repository, the site that serves it,
the database behind it, the DNS name staff type, the survey answer, the bill.
They are joined by the keys they actually share, never by name:

    site -> repository        the site's linked repository
    repository -> site        the site id in the repository's CLI state
    repository -> Firebase    the project named in .firebaserc
    repository -> Supabase    the project URL in the code
    DNS name -> site          the record's target
    survey -> anything        the repository, URL or agent id the builder gave

Connected pieces are one tool. When the evidence conflicts - two
repositories both deploying one site - the tool is registered and the
conflict is held for a person, not guessed. A DNS name that points at
nothing any export contains is a finding of its own: whoever registers that
site name receives the traffic.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

import duckdb

from src.app.pipeline import reference as ref

SENSITIVE = ("date_of_birth", "dob", "licence", "passport", "id_document", "payslip", "income")
FINANCIAL = ("bsb", "account_no", "bond", "rent", "arrears", "budget", "spent", "commission")
PERSON = ("name", "email", "phone", "mobile", "issued_to")
PUBLIC_ONLY = {"listing_address", "suburb", "result", "sale_price_cents", "auction_date"}


def classify_columns(columns: list[str]) -> set[str]:
    """Data classes from column names. Public only when every column is."""
    classes = set()
    for c in columns:
        if any(s in c for s in SENSITIVE):
            classes.add("sensitive")
        if any(s in c for s in FINANCIAL):
            classes.add("financial")
        if any(s in c for s in PERSON) and not c.startswith("agent_"):
            classes.add("personal")
    if columns and all(c in PUBLIC_ONLY for c in columns):
        return {"public"}
    if "agent_name" in columns:
        classes.add("staff performance")
    return classes or {"internal"}


def tier_for(classes: set[str], users: int) -> tuple[int, str]:
    if "sensitive" in classes:
        return 1, "holds identity documents or income"
    if "financial" in classes and "personal" in classes:
        return 1, "holds personal and financial data together"
    if users >= 60:
        return 1, f"{users} people used it in 30 days"
    if "personal" in classes or "staff performance" in classes:
        return 2, "holds personal information"
    return 3, "public or internal data only"


class Union:
    def __init__(self) -> None:
        self.parent: dict = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a, b) -> None:
        self.parent[self.find(a)] = self.find(b)


def run(con: duckdb.DuckDBPyConnection) -> dict:
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
    u = Union()
    edges: list[tuple[tuple, tuple, str]] = []

    repos = {r[0]: r for r in q("SELECT repo, owner_login, visibility FROM src_github_repos")}
    sites = {r[0]: r for r in q("SELECT site_id, site_name, account, repo_url, custom_domain, visitors_30d, requests_30d FROM src_netlify_sites")}
    site_by_host = {f"{r[1]}.netlify.app": r[0] for r in sites.values()}
    fb = {r[0]: r for r in q("SELECT project_id, account, hosting_url, collections, active_users_30d, requests_30d FROM src_firebase_projects")}
    fb_by_host = {r[2].replace("https://", ""): r[0] for r in fb.values()}
    sb = {r[0]: r for r in q("SELECT ref, name, account, plan, tables, active_users_30d, requests_30d FROM src_supabase_projects")}
    agents = {r[0]: r for r in q("SELECT agent_id, name, owner_upn, connectors, users_30d FROM src_copilot_agents")}
    dns = {r[0]: r[2] for r in q("SELECT name, type, target FROM src_dns WHERE type = 'CNAME'")}
    survey = {r[0]: r for r in q("SELECT response_id, upn, tool_name, process, purpose, repo, url, agent_id, users_estimate FROM src_survey")}
    files = q("SELECT repo, path, content FROM src_repo_files WHERE in_head")

    def link(a, b, why):
        u.join(a, b)
        edges.append((a, b, why))

    for k in repos:
        u.find(("repo", k))
    for k, r in sites.items():
        u.find(("netlify", k))
        if r[3]:
            link(("netlify", k), ("repo", r[3].replace("https://github.com/", "")), "the site's linked repository")
    for k in fb:
        u.find(("firebase", k))
    for k in sb:
        u.find(("supabase", k))
    for k in agents:
        u.find(("agent", k))
    for repo, path, content in files:
        if path == ".netlify/state.json":
            sid = json.loads(content).get("siteId")
            if sid in sites:
                link(("repo", repo), ("netlify", sid), "site id in the repository's CLI state")
        elif path == ".firebaserc":
            pid = json.loads(content).get("projects", {}).get("default")
            if pid in fb:
                link(("repo", repo), ("firebase", pid), "project named in .firebaserc")
        for m in re.finditer(r"https://([a-z]{16})\.supabase\.co", content):
            if m.group(1) in sb:
                link(("repo", repo), ("supabase", m.group(1)), "project URL in the code")

    dangling = []
    for name, target in dns.items():
        if not name.endswith(ref.DOMAIN) or name.count(".") < 2:
            continue
        if target in site_by_host:
            link(("dns", name), ("netlify", site_by_host[target]), "DNS record target")
        elif target in fb_by_host:
            link(("dns", name), ("firebase", fb_by_host[target]), "DNS record target")
        elif target.endswith((".netlify.app", ".web.app", ".firebaseapp.com")):
            dangling.append((name, target))

    for rid, r in survey.items():
        node = ("survey", rid)
        u.find(node)
        if r[5]:
            link(node, ("repo", r[5].replace("https://github.com/", "")), "repository given in the survey")
        if r[6]:
            host = r[6].replace("https://", "")
            if host in dns:
                link(node, ("dns", host), "URL given in the survey")
            elif host in site_by_host:
                link(node, ("netlify", site_by_host[host]), "URL given in the survey")
        if r[7] and r[7] in agents:
            link(node, ("agent", r[7]), "agent id given in the survey")

    groups: dict = defaultdict(list)
    for node in list(u.parent):
        groups[u.find(node)].append(node)

    # ---- Owners: survey, then the account's declared identity, then HR -------
    identity = defaultdict(dict)
    for upn, platform, acct in q("SELECT upn, platform, account FROM src_identity"):
        identity[platform][acct] = upn
    hr = {r[0]: r for r in q("SELECT upn, display_name, role, office, status, left_on FROM src_staff")}

    def owner_of(account: str | None, gh_login: str | None) -> tuple[str | None, str]:
        if account and account in identity["email"]:
            return identity["email"][account], "account declared in the survey"
        if account and account.endswith("@" + ref.STAFF_DOMAIN) and account in hr:
            return account, "work address on the account"
        if gh_login and gh_login in identity["github"]:
            return identity["github"][gh_login], "GitHub login declared in the survey"
        return None, "no owner found"

    tools, sources, holds, flags = [], [], [], []
    n = 0
    for members in sorted(groups.values(), key=lambda g: sorted(map(str, g))):
        kinds = defaultdict(list)
        for kind, key in members:
            kinds[kind].append(key)
        if set(kinds) == {"dns"}:
            continue
        if set(kinds) == {"survey"}:
            r = survey[kinds["survey"][0]]
            holds.append((None, "survey", r[0], "The survey names a tool no export contains.", r[2], None))
            continue
        n += 1
        tid = f"T-{n:03d}"
        srv = survey[kinds["survey"][0]] if kinds["survey"] else None
        repo_list = sorted(kinds["repo"])
        repo = repo_list[0] if len(repo_list) == 1 else None
        if len(repo_list) > 1:
            holds.append((None, "github", ", ".join(repo_list),
                          "More than one repository deploys this site by CLI; which one is production cannot be told from the exports.",
                          tid, None))
        site = sites[kinds["netlify"][0]] if kinds["netlify"] else None
        proj = fb[kinds["firebase"][0]] if kinds["firebase"] else None
        sbp = sb[kinds["supabase"][0]] if kinds["supabase"] else None
        agent = agents[kinds["agent"][0]] if kinds["agent"] else None
        host = kinds["dns"][0] if kinds["dns"] else (f"{site[1]}.netlify.app" if site else (proj[2].replace("https://", "") if proj else None))

        account = (site and site[2]) or (proj and proj[1]) or (sbp and sbp[2])
        gh = repos[repo_list[0]][1] if repo_list else None
        if srv:
            owner, owner_how = srv[1], "the survey"
        elif agent:
            owner, owner_how = agent[2], "agent owner"
        else:
            owner, owner_how = owner_of(account, gh)
        person = hr.get(owner) if owner else None

        name = srv[2] if srv else (site[1] if site else proj[0] if proj else sbp[1] if sbp else repo_list[0].split("/")[1])
        kind = "agent" if agent else ("web" if (site or proj or sbp) else "script")
        columns_by_table = []
        records = 0
        if proj:
            for c in json.loads(proj[3]):
                columns_by_table.append(c["fields"])
                records += c["docs"]
        if sbp:
            for t in json.loads(sbp[4]):
                columns_by_table.append(t["columns"])
                records += t["rows"]
        classes: set[str] = set()
        for cols in columns_by_table:
            classes |= classify_columns(cols)
        code_text = " ".join(c for r, p, c in files if r in repo_list)
        ai_route = None
        if agent:
            ai_route = "Copilot Studio"
            conns = json.loads(agent[3])
            if any("Outlook" in c or "Gmail" in c or "Dropbox" in c for c in conns):
                classes.add("personal")
        elif "@anthropic-ai/sdk" in code_text or "from \"openai\"" in code_text or "import OpenAI" in code_text:
            ai_route = "AI gateway" if any(h in code_text for h in ref.APPROVED_AI_HOSTS) else "direct API, personal key"
            for m in re.findall(r"\$\{\w+\.(\w+)\}", code_text):
                classes |= classify_columns([m]) - {"internal"}
        if kind == "script":
            if re.search(r"BANK_FEED|trust", code_text, re.I):
                classes.add("financial")
            elif re.search(r"price|listing", code_text, re.I):
                classes.add("public")
        if not classes or (classes == {"internal"} and not columns_by_table and kind == "web"):
            classes = classes or {"internal"}
        if len(classes) > 1:
            classes.discard("internal")
            if classes != {"public"}:
                classes.discard("public")

        users = max([site[5] if site else 0, proj[4] if proj else 0, sbp[5] if sbp else 0, agent[4] if agent else 0])
        if kind == "script" and srv:
            users = srv[8]
        requests = (site[6] if site else 0) + (proj[5] if proj else 0) + (sbp[6] if sbp else 0)
        tier, why = tier_for(classes, users)
        key = (repo_list[0].split("/")[1] if repo_list and repo else (agent[0] if agent else (site[1] if site else (proj[0] if proj else name))))
        tools.append((tid, key, name, bool(srv), srv[3] if srv else None, srv[4] if srv else None, kind,
                      owner, person[1] if person else None, person[2] if person else None, person[3] if person else None,
                      person[4] if person else "unknown", person[5] if person else None,
                      repo, ", ".join(repo_list) if len(repo_list) > 1 else None, repos[repo_list[0]][2] if repo_list else None,
                      "netlify" if site else ("firebase" if proj else None), site[1] if site else (proj[0] if proj else None),
                      "supabase" if sbp else ("firestore" if proj and json.loads(proj[3]) else None), sbp[0] if sbp else None,
                      host, agent[0] if agent else None, ai_route, users, requests, records, ", ".join(sorted(classes)),
                      tier, why, 0, None, "personal accounts", "in use" if users else "idle", len(members)))
        for kind_, key_ in sorted(members, key=str):
            how = "the survey" if kind_ == "survey" else next((w for a, b, w in edges if (kind_, key_) in (a, b)), "anchor")
            sources.append((tid, kind_, str(key_), how))
        if owner_how == "no owner found":
            flags.append((tid, "no_owner", "critical", "No export or survey answer names an owner."))

    for name, target in dangling:
        flags.append((None, "dangling_dns", "critical",
                      f"{name} points at {target}, which no export contains. Whoever creates that site name receives this traffic."))

    con.executemany(f"INSERT INTO tool VALUES ({', '.join('?' * 34)})", tools)
    con.executemany("INSERT INTO tool_source VALUES (?, ?, ?, ?)", sources)
    for i, h in enumerate(holds, start=1):
        con.execute("INSERT INTO discovery_hold VALUES (?, ?, ?, ?, ?, ?)", [f"H-{i:02d}", *h[1:]])
    if flags:
        con.executemany("INSERT INTO register_flag VALUES (?, ?, ?, ?)", flags)
    _flags(con)
    return {"tools": len(tools), "holds": len(holds), "dangling_dns": len(dangling)}


def _flags(con: duckdb.DuckDBPyConnection) -> None:
    """Register-level flags, each from the joined data."""
    con.execute("""INSERT INTO register_flag
        SELECT tool_id, 'orphaned', 'critical',
               'Owner left on ' || strftime(owner_left_on, '%d/%m/%Y') || '; ' || users_30d || ' people used it in the last 30 days.'
        FROM tool WHERE owner_status = 'left' AND users_30d > 0""")
    con.execute("""INSERT INTO register_flag
        SELECT tool_id, 'owner_left_idle', 'warning', 'Owner has left and nobody used it in 30 days: a retirement candidate.'
        FROM tool WHERE owner_status = 'left' AND users_30d = 0""")
    con.execute("""INSERT INTO register_flag
        SELECT tool_id, 'undeclared', 'warning', 'Found in the exports; nobody declared it in the survey.'
        FROM tool WHERE NOT declared""")
    con.execute("""INSERT INTO register_flag
        SELECT tool_id, 'public_repo', CASE WHEN data_classes <> 'public' THEN 'warning' ELSE 'info' END,
               'The repository is public on a personal account.'
        FROM tool WHERE repo_visibility = 'public'""")
    con.execute("""INSERT INTO register_flag
        SELECT t.tool_id, 'duplicate_process', 'warning',
               'Another tool supports the same process (' || t.process || '): ' || string_agg(o.name, ', ') || '.'
        FROM tool t JOIN tool o ON o.process = t.process AND o.tool_id <> t.tool_id
        WHERE t.process IS NOT NULL GROUP BY t.tool_id, t.process""")
    con.execute("""INSERT INTO register_flag
        SELECT tool_id, 'idle', 'info', 'Nobody used it in 30 days.' FROM tool WHERE users_30d = 0 AND owner_status <> 'left'""")


def ai_register(con: duckdb.DuckDBPyConnection) -> None:
    """Every AI route in use, from the evidence: expense claims, code, agents."""
    rows = []
    for vendor, label in (("Anthropic (Claude Pro)", "Claude, personal subscriptions"), ("OpenAI (ChatGPT Plus)", "ChatGPT, personal subscriptions")):
        n = con.execute("SELECT count(DISTINCT upn) FROM src_expenses WHERE vendor = ? AND month = ?", [vendor, ref.BILLING_MONTHS[-1]]).fetchone()[0]
        rows.append((label, "personal subscription on an expense claim", False, "none: no admin controls, no record of what was shared",
                     n, None, f"{n} claimants for {vendor} in {ref.BILLING_MONTHS[-1]}"))
    for label, needle in (("Anthropic API, direct with a personal key", "@anthropic-ai/sdk"), ("OpenAI API, direct with a personal key", "openai")):
        tools = [r[0] for r in con.execute(
            "SELECT name FROM tool WHERE ai_route = 'direct API, personal key' AND tool_id IN (SELECT t.tool_id FROM tool t JOIN src_repo_files f "
            "ON f.repo = t.repo AND f.in_head AND f.path = 'package.json' AND f.content LIKE ?) ORDER BY 1", [f'%"{needle}"%']).fetchall()]
        approved, allowed = ref.APPROVED_AI_TOOLS[label]
        rows.append((label, "called from tool code", approved, allowed, len(tools), ", ".join(tools), "found by scanning each repository"))
    agents = con.execute("SELECT string_agg(name, ', ' ORDER BY name), count(*), sum(users_30d) FROM tool WHERE ai_route = 'Copilot Studio'").fetchone()
    approved, allowed = ref.APPROVED_AI_TOOLS["Microsoft Copilot Studio"]
    rows.append(("Microsoft Copilot Studio", "agents in the tenant", approved, allowed, agents[2], agents[0], f"{agents[1]} agents in the export"))
    for label in ("GitHub Copilot", "Claude Code", "Anthropic API via the AI gateway", "Azure OpenAI (sandbox)"):
        approved, allowed = ref.APPROVED_AI_TOOLS[label]
        rows.append((label, "approved route", approved, allowed, 0, None, "approved in the policy; no use measured in the exports yet"))
    con.executemany("INSERT INTO ai_register VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
