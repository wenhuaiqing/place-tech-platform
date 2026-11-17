"""Cloud cost: what the tools cost, who pays, and what can go.

Platform bills are in US dollars and converted at one assumed rate
(reference.AUD_PER_USD_BP, labelled wherever it is used). An account-level
plan - Netlify Pro is per member, not per site - is split evenly across the
account's sites, and the basis is written on every line. Expense claims are
matched to the bill they pay by person, platform and month, within 5%: a
claim nothing matches is held, not guessed at.
"""

from __future__ import annotations

from collections import defaultdict

import duckdb

from src.app.pipeline import reference as ref
from src.app.pipeline.generate import aud

PLATFORM_OF_VENDOR = {"Netlify": "netlify", "Supabase": "supabase", "Google Cloud": "firebase", "Anthropic": "anthropic", "OpenAI": "openai"}
AI_SUBSCRIPTIONS = {"Anthropic (Claude Pro)", "OpenAI (ChatGPT Plus)"}

# Planning figures for the consolidated target, A$ cents a month. ASSUMPTIONS,
# not quotes: replace them with the Azure pricing calculator for the agreed design.
TARGET_PLAN = [
    ("Azure Container Apps, one shared environment (consumption)", 2_000),
    ("Azure Database for PostgreSQL flexible server, one shared (burstable)", 9_000),
    ("Azure Static Web Apps for the static tools (free plan)", 0),
    ("Log Analytics, capped", 1_500),
    ("AI gateway (API Management, consumption) plus model usage at today's volume", 12_000),
    ("GitHub Team seats for builders (assumed 12)", 7_500),
]


def run(con: duckdb.DuckDBPyConnection) -> dict:
    q = lambda sql, p=None: con.execute(sql, p or []).fetchall()  # noqa: E731
    lines = []
    sites_by_account = defaultdict(list)
    for site, acct in q("SELECT site_name, account FROM src_netlify_sites ORDER BY site_name"):
        sites_by_account[acct].append(site)
    tool_by_site = {s: t for t, s in q("SELECT tool_id, site FROM tool WHERE site IS NOT NULL")}
    tool_by_ref = {r: t for t, r in q("SELECT tool_id, db_ref FROM tool WHERE db_ref IS NOT NULL")}
    owner_account = {}
    for upn, acct in q("SELECT upn, account FROM src_identity WHERE platform = 'email'"):
        owner_account[acct] = upn
    for (upn,) in q("SELECT upn FROM src_staff"):
        owner_account.setdefault(upn, upn)
    ai_tools_by_account = defaultdict(list)
    for tid, owner in q("SELECT tool_id, owner_upn FROM tool WHERE ai_route = 'direct API, personal key' ORDER BY tool_id"):
        for acct, upn in owner_account.items():
            if upn == owner and not acct.endswith(ref.STAFF_DOMAIN):
                ai_tools_by_account[acct].append(tid)

    for month, platform, acct, resource, _cur, cents in q("SELECT * FROM src_billing ORDER BY month, platform, account, resource"):
        total = aud(cents)
        if platform == "netlify":
            sites = sites_by_account.get(acct, [])
            share, rest = divmod(total, max(1, len(sites)))
            for i, s in enumerate(sites):
                lines.append((month, platform, acct, s, tool_by_site.get(s), share + (rest if i == 0 else 0),
                              f"Netlify Pro for the account, split across its {len(sites)} sites"))
        elif platform == "supabase":
            lines.append((month, platform, acct, resource, tool_by_ref.get(resource), total, "project plan and compute"))
        elif platform == "firebase":
            lines.append((month, platform, acct, resource, tool_by_site.get(resource), total, "project usage (Blaze plan)"))
        else:
            tids = ai_tools_by_account.get(acct, [])
            share, rest = divmod(total, max(1, len(tids)))
            if tids:
                for i, t in enumerate(tids):
                    lines.append((month, platform, acct, resource, t, share + (rest if i == 0 else 0), "model API usage on the owner's key"))
            else:
                lines.append((month, platform, acct, resource, None, total, "model API usage, no tool found for the key"))
    for name, _type, cents in q("SELECT * FROM src_azure_resources"):
        lines.append((ref.BILLING_MONTHS[-1], "azure", "Place sandbox subscription", name, None, cents, "Azure sandbox resource"))
    for month, vendor, total in q(f"""SELECT month, vendor, sum(amount_aud_cents) FROM src_expenses
                                      WHERE vendor IN ({', '.join('?' * len(AI_SUBSCRIPTIONS))}) GROUP BY 1, 2 ORDER BY 1, 2""",
                                   sorted(AI_SUBSCRIPTIONS)):
        lines.append((month, "ai-subscriptions", "expense claims", vendor, None, total, "personal subscriptions claimed back"))
    con.executemany("INSERT INTO cost_line VALUES (?, ?, ?, ?, ?, ?, ?)", lines)

    # ---- Expense claims against bills ------------------------------------------
    billed = defaultdict(int)
    for month, platform, acct, cents in q("SELECT month, platform, account, sum(amount_cents) FROM src_billing GROUP BY 1, 2, 3"):
        billed[(month, platform, acct)] = aud(cents)
    accounts_of = defaultdict(set)
    for acct, upn in owner_account.items():
        accounts_of[upn].add(acct)
    claimed_accounts = defaultdict(set)
    unmatched = {}
    for _cid, upn, month, vendor, _desc, amount in q("SELECT * FROM src_expenses ORDER BY claim_id"):
        if vendor in AI_SUBSCRIPTIONS:
            continue
        platform = PLATFORM_OF_VENDOR.get(vendor)
        hit = None
        if platform:
            for acct in sorted(accounts_of[upn]):
                bill = billed.get((month, platform, acct))
                if bill and abs(amount - bill) * 100 <= bill * 5:
                    hit = acct
        if hit:
            claimed_accounts[month].add(hit)
        else:
            unmatched.setdefault((upn, vendor), []).append((month, amount))
    n0 = con.execute("SELECT count(*) FROM discovery_hold").fetchone()[0]
    for i, ((upn, vendor), claims) in enumerate(sorted(unmatched.items()), start=n0 + 1):
        con.execute("INSERT INTO discovery_hold VALUES (?, 'expenses', ?, ?, ?, NULL)",
                    [f"H-{i:02d}", f"{upn}: {vendor}",
                     f"Paid on {len(claims)} expense claim(s) (latest A${claims[-1][1] / 100:,.2f}); no export has a matching resource. Ask the claimant.",
                     ", ".join(m for m, _ in claims)])

    # ---- Tool cost and who pays -----------------------------------------------
    last = ref.BILLING_MONTHS[-1]
    for tid, cents in q("SELECT tool_id, sum(aud_cents) FROM cost_line WHERE month = ? AND tool_id IS NOT NULL GROUP BY 1", [last]):
        con.execute("UPDATE tool SET monthly_cost_aud_cents = ? WHERE tool_id = ?", [cents, tid])
    for tid, owner_status in q("SELECT tool_id, owner_status FROM tool"):
        accts = {a for (a,) in q("SELECT DISTINCT account FROM cost_line WHERE tool_id = ? AND month = ?", [tid, last])}
        if not accts:
            paid = "free plan, no bill"
        elif accts & claimed_accounts[last]:
            paid = "personal card, claimed back"
        elif owner_status == "left":
            paid = "a leaver's card; nobody claims it"
        else:
            paid = "personal card, not claimed"
        con.execute("UPDATE tool SET paid_by = ? WHERE tool_id = ?", [paid, tid])

    _findings(con)
    return {"lines": len(lines), "unmatched_claims": len(unmatched)}


def _findings(con: duckdb.DuckDBPyConnection) -> None:
    q = lambda sql, p=None: con.execute(sql, p or []).fetchall()  # noqa: E731
    last = ref.BILLING_MONTHS[-1]
    rows = []

    def add(kind, tool_id, resource, cents, detail, action):
        rows.append((f"C-{len(rows) + 1:02d}", kind, tool_id, resource, cents, detail, action))

    for tid, name, cents in q("SELECT tool_id, name, monthly_cost_aud_cents FROM tool WHERE users_30d = 0 AND monthly_cost_aud_cents > 0 ORDER BY 1"):
        add("idle", tid, name, cents, f"{name} cost A${cents / 100:,.2f} last month and nobody used it in 30 days.", "Retire it")
    for tid, name, ref_id, users, size in q("""SELECT t.tool_id, t.name, s.ref, t.users_30d, s.db_size_mb FROM tool t
                                               JOIN src_supabase_projects s ON s.ref = t.db_ref
                                               WHERE s.plan = 'pro' AND t.users_30d BETWEEN 1 AND 4 AND s.db_size_mb < 500 ORDER BY 1"""):
        cents = con.execute("SELECT sum(aud_cents) FROM cost_line WHERE month = ? AND resource = ?", [last, ref_id]).fetchone()[0]
        add("oversized", tid, ref_id, cents, f"{name} pays for a Pro project for {users} users and {size} MB; the free plan holds 500 MB.",
            "Move it to the free plan, or into the shared database")
    for process, names, cents, tid in q("""
            WITH d AS (SELECT process, tool_id, name, users_30d, monthly_cost_aud_cents,
                              row_number() OVER (PARTITION BY process ORDER BY users_30d DESC, tool_id) AS rk,
                              count(*) OVER (PARTITION BY process) AS n FROM tool WHERE process IS NOT NULL)
            SELECT process, (SELECT string_agg(name, ' and ' ORDER BY rk) FROM d d2 WHERE d2.process = d.process), monthly_cost_aud_cents, tool_id
            FROM d WHERE n > 1 AND rk = 2 ORDER BY 1"""):
        add("duplicate", tid, process, cents, f"{names} both support {process}.", "Merge into the more used one; retire the other")
    for tid, name, owner, cents in q("""SELECT tool_id, name, owner_name, monthly_cost_aud_cents FROM tool
                                        WHERE paid_by = 'a leaver''s card; nobody claims it' ORDER BY 1"""):
        add("leaver_billing", tid, name, cents, f"{name} is billed to {owner}'s account; {owner} has left and nobody claims it. It stops when the card does.",
            "Move it to a Place account before it is suspended")
    for acct, month, cents, before in q("""
            WITH m AS (SELECT account, month, sum(aud_cents) AS c FROM cost_line WHERE platform IN ('anthropic', 'openai') GROUP BY 1, 2)
            SELECT a.account, a.month, a.c, (SELECT median(c) FROM m b WHERE b.account = a.account AND b.month < a.month)
            FROM m a WHERE a.month = (SELECT max(month) FROM m) ORDER BY 1"""):
        if before and cents > 3 * before:
            tid = q("SELECT tool_id FROM cost_line WHERE account = ? AND month = ? AND tool_id IS NOT NULL LIMIT 1", [acct, month])
            add("runaway", tid[0][0] if tid else None, acct, cents - int(before),
                f"Model API spend in {month} was A${cents / 100:,.2f} against a usual A${before / 100:,.2f}.",
                "Cap spend per key at the gateway; alert at twice the usual")
    for name, typ, cents in q("""SELECT name, type, monthly_aud_cents FROM src_azure_resources
                                 WHERE name NOT IN (SELECT name FROM src_tf_state) ORDER BY 1"""):
        add("drift", None, name, cents, f"{name} ({typ}) is in the sandbox subscription but not in Terraform.", "Import it into Terraform, or delete it")
    subs = q("SELECT vendor, count(*), sum(amount_aud_cents) FROM src_expenses WHERE month = ? AND vendor LIKE '%(%' GROUP BY 1 ORDER BY 1", [last])
    for vendor, n, cents in subs:
        add("personal_ai", None, vendor, cents, f"{n} people claim a personal {vendor} subscription.",
            "Replace with a managed plan the AI policy approves; no saving assumed")
    con.executemany("INSERT INTO cost_finding VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
