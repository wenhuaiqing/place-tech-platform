"""Monitoring for the tools that serve staff: four weeks of alerts, the rules
that cut the noise, and the evidence each incident's triage starts from.

Generation seeds the noise a small estate really has - a probe region that
flaps, one check configured in two monitors, the nightly deploy window, a
scale-to-zero app that is slow on its first request - and seven real
incidents among it. The rules are judged on two numbers kept apart: pages
to a person (fewer is better) and incidents paged (all of them, or the rule
is wrong). Every alternative setting tried is kept with what it would have
missed, so "we cut the noise" comes with "and here is what it did not hide".

The incident snapshots are what the triage agent may see. Personal details
in the logs are masked before the snapshot is taken.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import duckdb

from src.app.pipeline import reference as ref

REGIONS = ["syd", "mel", "sgp"]
THRESHOLD = {"latency_p95": 1500, "http_5xx_rate": 2, "uptime_probe": 1, "dependency_auth_failures": 5, "db_write_errors": 1,
             "db_connections": 54, "tls_handshake_failures": 1, "cost_anomaly": 300, "function_invocations": 5000}
PROBE_SIGNALS = {"uptime_probe", "tls_handshake_failures"}


def resource(key: str) -> str:
    t = next(t for t in ref.TOOLS if t["key"] == key)
    return t.get("site") or t.get("project")


def _provider(key: str) -> str:
    t = next(t for t in ref.TOOLS if t["key"] == key)
    return "Netlify" if t.get("hosting") == "netlify" else "Firebase"


def generate(con: duckdb.DuckDBPyConnection) -> int:
    rng = random.Random(ref.SEED + 1)
    alerts: list[list] = []
    logs, deploys, config, provider = [], [], [], []

    def alert(ts, key, signal, *, monitor="azure-monitor", region=None, value=None, after_idle=False, incident=None, severity="warning"):
        thr = THRESHOLD[signal]
        alerts.append([ts, resource(key), monitor, signal, region, severity, f"{resource(key)}:{signal}",
                       value if value is not None else thr * (110 + rng.randrange(40)) // 100, thr, after_idle, incident])

    start = ref.ALERT_START
    for d in range(ref.ALERT_DAYS):
        day = start + timedelta(days=d)
        for key in ref.MONITORED:
            # Background: an occasional slow minute in business hours.
            if rng.randrange(100) < 15:
                alert(day + timedelta(hours=8 + rng.randrange(10), minutes=rng.randrange(60)), key, "latency_p95")
            # The nightly deploy and restart.
            if rng.randrange(100) < 55:
                for _ in range(1 + rng.randrange(2)):
                    alert(day + timedelta(hours=2, minutes=1 + rng.randrange(14)), key, "uptime_probe", region=REGIONS[rng.randrange(3)])
                if rng.randrange(100) < 25:
                    alert(day + timedelta(hours=2, minutes=3 + rng.randrange(12)), key, "http_5xx_rate")
        # A scale-to-zero app, slow on the first request each weekday morning.
        if day.weekday() < 5:
            alert(day + timedelta(hours=8, minutes=rng.randrange(10)), ref.NOISE["cold_start_latency"], "latency_p95",
                  value=4_200 + rng.randrange(1_500), after_idle=True)
        # Month-end commission run: slow for twenty minutes, nobody affected.
        if d == ref.NOISE_BUSY_DAY:
            for i in range(4):
                alert(day + timedelta(hours=16, minutes=2 + i * 6), ref.NOISE["busy_but_fine"], "latency_p95", value=1_560 + i * 40)
                logs.append((resource(ref.NOISE["busy_but_fine"]), day + timedelta(hours=16, minutes=3 + i * 6), "info",
                             f"GET /api/split {1_560 + i * 40} ms (month-end run, {180 + i * 25} requests, 0 errors)"))
        # One probe region flapping for two days.
        if d in (4, 5):
            for m in range(0, 24 * 60, 10):
                alert(day + timedelta(minutes=m), ref.NOISE["flapping_probe"], "uptime_probe", monitor="uptime-probe", region="sgp")

    # ---- The incidents ------------------------------------------------------
    for iid, (key, hours, cat) in ref.INCIDENTS.items():
        t0 = start + timedelta(hours=hours)
        res = resource(key)

        def burst(signal, n, every, offset=0, regions=None, value=None, severity="critical"):
            for i in range(n):
                alert(t0 + timedelta(minutes=offset + i * every), key, signal, region=regions[i % len(regions)] if regions else None,
                      value=value(i) if value else None, incident=iid, severity=severity)

        def log(minute, level, line):
            logs.append((res, t0 + timedelta(minutes=minute), level, line))

        if cat == "bad_deploy":
            deploys.append((res, t0 - timedelta(minutes=9), "7e1c2a9", json.dumps(["netlify/functions/reports.js", "src/Report.jsx"]),
                            "Add buyer feedback section to the weekly report"))
            burst("http_5xx_rate", 12, 3, value=lambda i: 9 + i % 5)
            burst("latency_p95", 3, 10, offset=4)
            for i in range(6):
                log(i * 5, "error", "TypeError: report.feedback is not iterable at handler (reports.js:41:22)")
            log(2, "info", "report requested by jane.citizen@mail.example for 14 Example St")
            log(7, "info", "report requested by sam.vendor@mail.example, phone 0400 123 456")
        elif cat == "expired_secret":
            config.append((res, t0 - timedelta(hours=20), "Model API key 'appraisal' revoked in the provider console", "noahb.dev@mail.example"))
            burst("dependency_auth_failures", 10, 4, value=lambda i: 40 + i * 3)
            burst("http_5xx_rate", 3, 12, offset=2)
            for i in range(5):
                log(i * 8, "error", "AuthenticationError: 401 {\"type\":\"error\",\"error\":{\"type\":\"authentication_error\",\"message\":\"invalid x-api-key\"}}")
            log(3, "info", "draft requested for vendor m.owner@mail.example")
        elif cat == "upstream_outage":
            provider.append(("Netlify", t0 - timedelta(minutes=6), t0 + timedelta(minutes=50), "degraded",
                             "Elevated errors at the edge in the Australia region"))
            burst("uptime_probe", 8, 5, regions=["syd", "mel"])
            alerts_other = "commission-calc"
            for i in range(4):
                alert(t0 + timedelta(minutes=2 + i * 6), alerts_other, "uptime_probe", region=["syd", "mel"][i % 2], incident=iid, severity="critical")
            log(1, "warn", "probe syd: timeout after 10000 ms (edge 503)")
            log(6, "warn", "probe mel: timeout after 10000 ms (edge 503)")
        elif cat == "quota_exhausted":
            burst("db_write_errors", 9, 5, value=lambda i: 20 + i * 4)
            burst("http_5xx_rate", 2, 15, offset=3)
            for i in range(4):
                log(i * 9, "error", "ERROR: cannot execute INSERT in a read-only transaction (project exceeded the free plan's 500 MB database size)")
        elif cat == "db_connection_exhaustion":
            deploys.append((res, t0 - timedelta(days=2, hours=3), "3b9d0f1", json.dumps(["README.md"]), "Update the README"))
            burst("latency_p95", 3, 5, value=lambda i: 2_400 + i * 600)
            burst("db_connections", 8, 4, offset=25, value=lambda i: 58 + i % 3)
            burst("http_5xx_rate", 2, 10, offset=30)
            for i in range(5):
                log(25 + i * 6, "error", "FATAL: remaining connection slots are reserved for non-replication superuser connections")
            log(27, "info", "contract opened by buyer k.purchaser@mail.example")
        elif cat == "cert_expiry":
            config.append((res, t0 - timedelta(days=4), "Certificate renewal failed: DNS verification for the custom domain did not complete", "system"))
            burst("tls_handshake_failures", 10, 3, regions=REGIONS)
            burst("uptime_probe", 3, 9, offset=1, regions=REGIONS)
            log(0, "error", f"certificate has expired (CERT_HAS_EXPIRED) for suburbs.{ref.DOMAIN}")
        elif cat == "runaway_cost":
            deploys.append((res, t0 - timedelta(hours=26), "c4f2e88", json.dumps(["netlify/functions/draft.js"]), "Retry the draft when the model is busy"))
            burst("cost_anomaly", 1, 1, value=lambda i: 1_870)
            burst("function_invocations", 6, 10, offset=2, value=lambda i: 41_000 + i * 1_500)
            for i in range(5):
                log(i * 11, "warn", f"RateLimitError 429 from the model API; retrying (attempt {1_400 + i * 120})")

    # Quiet logs on the noise, so a blip has evidence too.
    for a in alerts:
        if a[10] is None and a[3] == "latency_p95" and not a[9] and rng.randrange(100) < 30:
            logs.append((a[1], a[0], "info", f"GET /api slow response {a[7]} ms (single request)"))

    alerts.sort(key=lambda a: (a[0], a[1], a[3], a[2], a[4] or ""))
    rows = []
    dup_key = resource(ref.NOISE["duplicate_monitor"])
    n = 0
    for a in alerts:
        n += 1
        rows.append((f"A-{n:05d}", *a))
        # The same check, configured a second time in the site's own notifications.
        if a[1] == dup_key and a[2] == "azure-monitor":
            n += 1
            b = list(a)
            b[0] = a[0] + timedelta(minutes=1 + rng.randrange(3))
            b[2] = "netlify-notify"
            rows.append((f"A-{n:05d}", *b))
    con.executemany("INSERT INTO alert_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    con.executemany("INSERT INTO src_logs VALUES (?, ?, ?, ?)", sorted(logs))
    con.executemany("INSERT INTO src_deploys VALUES (?, ?, ?, ?, ?)", deploys)
    if config:
        con.executemany("INSERT INTO src_config_changes VALUES (?, ?, ?, ?)", config)
    con.executemany("INSERT INTO src_provider_status VALUES (?, ?, ?, ?, ?)", provider)
    return len(rows)


# ---- The noise rules ------------------------------------------------------------

# A page stays open while alerts keep arriving within group_minutes of each
# other, for at most two hours; after that the person is told again.
DEFAULT = {"maintenance": True, "dedupe": True, "cold_start": True, "probe_regions": 2, "persist": True, "group_minutes": 30,
           "drop_signals": (), "max_page_minutes": 120}


def process(alerts: list[tuple], settings: dict) -> tuple[list[tuple], list[dict]]:
    """alerts: (alert_id, ts, tool, monitor, signal, region, after_idle). Returns (decisions, pages)."""
    decisions = []
    kept = []
    seen: dict[tuple, tuple[datetime, str]] = {}
    h0, m0, h1, m1 = ref.MAINTENANCE
    for aid, ts, tool, monitor, signal, region, after_idle in alerts:
        if signal in settings["drop_signals"]:
            decisions.append((aid, "dropped signal", None))
            continue
        if settings["maintenance"] and (h0, m0) <= (ts.hour, ts.minute) < (h1, m1) and signal in ("uptime_probe", "http_5xx_rate", "latency_p95"):
            decisions.append((aid, "maintenance window", None))
            continue
        # The same check from a second monitor within five minutes is one
        # event. Each copy pairs with one original, so a copy never makes the
        # next real alert look like a copy.
        k = (tool, signal, region)
        prev = seen.pop(k, None)
        if settings["dedupe"] and prev and prev[1] != monitor and ts - prev[0] <= timedelta(minutes=5):
            decisions.append((aid, "duplicate from a second monitor", None))
            continue
        seen[k] = (ts, monitor)
        if settings["cold_start"] and after_idle:
            decisions.append((aid, "first request after idle", None))
            continue
        kept.append((aid, ts, tool, monitor, signal, region))
    # Probe confirmation: a probe failure counts when enough regions agree within 10 minutes.
    confirmed = []
    probes = defaultdict(list)
    for a in kept:
        if a[4] in PROBE_SIGNALS:
            probes[a[2]].append(a)
    for a in kept:
        if a[4] in PROBE_SIGNALS and settings["probe_regions"] > 1:
            near = {b[5] for b in probes[a[2]] if abs((b[1] - a[1]).total_seconds()) <= 600}
            if len(near) < settings["probe_regions"]:
                decisions.append((a[0], "one probe region only", None))
                continue
        confirmed.append(a)
    # Persistence: one slow minute is not a page. A latency alert pages when
    # a second one on the same tool follows within 15 minutes.
    if settings["persist"]:
        kept_latency = []
        last_latency: dict[str, datetime] = {}
        for a in confirmed:
            if a[4] == "latency_p95":
                prev = last_latency.get(a[2])
                last_latency[a[2]] = a[1]
                if not prev or a[1] - prev > timedelta(minutes=15):
                    decisions.append((a[0], "single slow minute", None))
                    continue
            kept_latency.append(a)
        confirmed = kept_latency
    # Group: one page per tool while alerts keep arriving within the window.
    pages: list[dict] = []
    open_page: dict[str, dict] = {}
    for aid, ts, tool, _mon, signal, _reg in confirmed:
        p = open_page.get(tool)
        if p and (ts - p["last"]) <= timedelta(minutes=settings["group_minutes"]) \
                and (ts - p["opened"]) <= timedelta(minutes=settings["max_page_minutes"]):
            p["alerts"].append(aid)
            p["signals"][signal] += 1
            p["last"] = ts
            decisions.append((aid, "grouped into an open page", p["page_id"]))
        else:
            p = {"page_id": f"P-{len(pages) + 1:04d}", "tool": tool, "opened": ts, "last": ts, "alerts": [aid], "signals": Counter({signal: 1})}
            pages.append(p)
            open_page[tool] = p
            decisions.append((aid, "paged", p["page_id"]))
    return decisions, pages


def _load(con) -> tuple[list[tuple], dict[str, str], dict[str, datetime]]:
    rows = con.execute("SELECT alert_id, ts, tool_key, monitor, signal, region, after_idle, incident_id FROM alert_raw ORDER BY ts, alert_id").fetchall()
    incident_of = {r[0]: r[7] for r in rows if r[7]}
    first = {}
    for r in rows:
        if r[7] and r[7] not in first:
            first[r[7]] = r[1]
    return [r[:7] for r in rows], incident_of, first


def _score(pages, incident_of, first) -> tuple[int, list[str], int]:
    """An incident is paged when its first surviving alert opens a page, or
    joins one opened at most 30 minutes before it. Folded into an older page,
    nobody is told anything new: that counts as missed."""
    paged_at = {}
    absorbed = set()
    for p in pages:
        for aid in p["alerts"]:
            iid = incident_of.get(aid)
            if not iid or iid in paged_at or iid in absorbed:
                continue
            if (first[iid] - p["opened"]) > timedelta(minutes=30):
                absorbed.add(iid)
            else:
                paged_at[iid] = max(p["opened"], first[iid])
    missed = sorted(set(ref.INCIDENTS) - set(paged_at))
    worst = max([int((paged_at[i] - first[i]).total_seconds() // 60) for i in paged_at] or [0])
    return len(paged_at), missed, worst


VARIANTS = [
    ("Every alert pages", "no rules", {"maintenance": False, "dedupe": False, "cold_start": False, "probe_regions": 1, "persist": False,
                                        "group_minutes": -1}),
    ("All rules", "as configured", {}),
    ("Without the maintenance window", "rule off", {"maintenance": False}),
    ("Without de-duplication", "rule off", {"dedupe": False}),
    ("Without the first-request rule", "rule off", {"cold_start": False}),
    ("Without probe confirmation", "rule off", {"probe_regions": 1}),
    ("Without the persistence rule", "rule off", {"persist": False}),
    ("Without grouping", "rule off", {"group_minutes": -1}),
    ("Drop all latency alerts", "tried and rejected", {"drop_signals": ("latency_p95",)}),
    ("Require all three probe regions", "tried and rejected", {"probe_regions": 3}),
]


def run(con: duckdb.DuckDBPyConnection) -> dict:
    alerts, incident_of, first = _load(con)
    decisions, pages = process(alerts, dict(DEFAULT))
    con.executemany("INSERT INTO alert_decision VALUES (?, ?, ?)", decisions)
    page_rows = []
    for p in pages:
        iids = sorted({incident_of[a] for a in p["alerts"] if a in incident_of})
        page_rows.append((p["page_id"], p["tool"], p["opened"], p["last"], len(p["alerts"]),
                          ", ".join(f"{s} x{n}" for s, n in p["signals"].most_common()), iids[0] if iids else None))
    con.executemany("INSERT INTO page VALUES (?, ?, ?, ?, ?, ?, ?)", page_rows)
    rows = []
    for name, setting, overrides in VARIANTS:
        s = {**DEFAULT, **overrides}
        _d, ps = process(alerts, s)
        paged, missed, worst = _score(ps, incident_of, first)
        rows.append((name, setting, len(ps), paged, ", ".join(missed) or None, worst))
    con.executemany("INSERT INTO noise_ablation VALUES (?, ?, ?, ?, ?, ?)", rows)
    _worlds(con)
    _forecasts(con)
    return {"alerts": len(alerts), "pages": len(pages)}


# ---- What the triage agent may see ---------------------------------------------------

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
PHONE = re.compile(r"\b04\d{2} ?\d{3} ?\d{3}\b")
NAME_AFTER = re.compile(r"(?<=for )\d+ [A-Z][a-z]+ (St|Rd|Ave)\b")


def mask(line: str) -> str:
    """Personal details out before anything is snapshotted for a model."""
    line = EMAIL.sub("[email]", line)
    line = PHONE.sub("[phone]", line)
    return NAME_AFTER.sub("[address]", line)


def world_for(con, tool: str, opened: datetime, closed: datetime) -> dict:
    lo, hi = opened - timedelta(hours=1), closed + timedelta(hours=1)
    alerts = con.execute("""SELECT r.ts, r.signal, r.region, r.value, r.threshold FROM alert_raw r
                            JOIN alert_decision d USING (alert_id) WHERE r.tool_key = ? AND d.page_id IN
                            (SELECT page_id FROM page WHERE tool_key = ? AND opened_at = ?) ORDER BY r.ts""", [tool, tool, opened]).fetchall()
    by_signal = Counter(a[1] for a in alerts)
    metrics = {}
    for _ts, sig, _reg, val, thr in alerts:
        k = f"{sig}_max"
        metrics[k] = max(metrics.get(k, 0), val)
        metrics[f"{sig}_threshold"] = thr
    growth = con.execute("""SELECT g.size_mb, g.limit_mb FROM src_db_growth g JOIN src_supabase_projects s ON s.ref = g.resource
                            JOIN src_netlify_sites n ON n.repo_url LIKE '%/' || s.name WHERE n.site_name = ? AND g.day = ?""",
                         [tool, opened.date()]).fetchone()
    if growth:
        metrics["db_size_mb"], metrics["db_limit_mb"] = growth
    provider_name = "Netlify" if con.execute("SELECT count(*) FROM src_netlify_sites WHERE site_name = ?", [tool]).fetchone()[0] else "Firebase"
    others = con.execute("""SELECT DISTINCT r.tool_key FROM alert_raw r JOIN alert_decision d USING (alert_id)
                            WHERE r.ts BETWEEN ? AND ? AND r.tool_key <> ? AND d.rule IN ('paged', 'grouped into an open page')""",
                         [lo, hi, tool]).fetchall()
    return {
        "get_alert_group": {"tool": tool, "opened_at": str(opened), "alerts": len(alerts), "by_signal": dict(by_signal),
                            "regions": sorted({a[2] for a in alerts if a[2]}), "first": str(alerts[0][0]) if alerts else None,
                            "last": str(alerts[-1][0]) if alerts else None},
        "get_recent_deploys": [{"at": str(r[0]), "commit": r[1], "files": json.loads(r[2]), "message": r[3]} for r in con.execute(
            "SELECT ts, commit_sha, files, message FROM src_deploys WHERE tool_key = ? AND ts BETWEEN ? AND ? ORDER BY ts",
            [tool, opened - timedelta(days=3), opened]).fetchall()],
        "get_error_logs": [{"at": str(r[0]), "level": r[1], "line": mask(r[2])} for r in con.execute(
            "SELECT ts, level, line FROM src_logs WHERE tool_key = ? AND ts BETWEEN ? AND ? ORDER BY ts LIMIT 10", [tool, lo, hi]).fetchall()],
        "get_metrics": metrics,
        "get_provider_status": {"provider": provider_name, "incidents": [
            {"provider": r[0], "from": str(r[1]), "to": str(r[2]), "status": r[3], "note": r[4]} for r in con.execute(
                "SELECT * FROM src_provider_status WHERE started_at <= ? AND ended_at >= ?", [hi, lo]).fetchall()],
            "other_tools_paging_same_window": [r[0] for r in others]},
        "get_config_changes": [{"at": str(r[0]), "change": mask(r[1]), "by": mask(r[2])} for r in con.execute(
            "SELECT ts, change, by_account FROM src_config_changes WHERE tool_key = ? AND ts BETWEEN ? AND ? ORDER BY ts",
            [tool, opened - timedelta(days=7), opened]).fetchall()],
    }


def _worlds(con) -> None:
    rows = []
    for iid in ref.INCIDENTS:
        key = ref.INCIDENTS[iid][0]
        p = con.execute("SELECT page_id, tool_key, opened_at, closed_at, signals FROM page WHERE incident_id = ? AND tool_key = ? ORDER BY opened_at LIMIT 1",
                        [iid, resource(key)]).fetchone()
        w = world_for(con, p[1], p[2], p[3])
        top = max(w["get_alert_group"]["by_signal"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        rows.append((iid, p[0], p[1], p[2], top, f"{top} on {p[1]}: {w['get_alert_group']['alerts']} alerts", json.dumps(w, default=str)))
    # The page the rules let through that was nothing: busy, not broken.
    p = con.execute("""SELECT page_id, tool_key, opened_at, closed_at FROM page WHERE incident_id IS NULL AND tool_key = ?
                       ORDER BY opened_at LIMIT 1""", [resource(ref.NOISE["busy_but_fine"])]).fetchone()
    w = world_for(con, p[1], p[2], p[3])
    rows.append(("CHK-01", p[0], p[1], p[2], "latency_p95", f"latency_p95 on {p[1]}: {w['get_alert_group']['alerts']} alerts", json.dumps(w, default=str)))
    con.executemany("INSERT INTO incident_world VALUES (?, ?, ?, ?, ?, ?, ?)", rows)


def _forecasts(con) -> None:
    """Straight-line trends, in integers. Simple on purpose: it says when, and why."""
    rows = []
    for res, in con.execute("SELECT DISTINCT resource FROM src_db_growth ORDER BY 1").fetchall():
        pts = con.execute("SELECT day, size_mb, limit_mb FROM src_db_growth WHERE resource = ? ORDER BY day DESC LIMIT 14", [res]).fetchall()
        now, limit = pts[0][1], pts[0][2]
        per_day_x100 = (pts[0][1] - pts[-1][1]) * 100 // max(1, (pts[0][0] - pts[-1][0]).days)
        days = (limit - now) * 100 // per_day_x100 if per_day_x100 > 0 else None
        rows.append((res, "database size (MB)", now, limit, per_day_x100, days,
                     ref.DEMO_TODAY + timedelta(days=days) if days is not None else None))
    for host, expires, auto in con.execute("SELECT hostname, expires_on, auto_renew FROM src_cert ORDER BY 1").fetchall():
        days = (expires - ref.DEMO_TODAY).days
        rows.append((host, "certificate expiry" + ("" if auto else " (auto-renew failing)"), days, 0, -100, days, expires))
    con.executemany("INSERT INTO forecast VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
