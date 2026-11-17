"""Build everything from nothing.

  1. land the raw exports: HR, survey, GitHub, Netlify, Firebase, Supabase,
     Copilot Studio, DNS, billing, expense claims, the Azure sandbox
  2. join them into one register of tools; hold what cannot be decided
  3. run the production gate over every tool, then price each check
  4. cost: allocate the bills, match the claims, find what can go
  5. monitoring: four weeks of alerts through the noise rules, incident snapshots
  6. the change history CAB has already seen, through the same governed path
  7. acceptance checks - a build that fails one is not a build
  8. check every table against the digests pinned in infra-azure/build.sha256

Usage (from backend/):
  uv run python ../scripts/build_platform.py              # build, verify against the manifest
  uv run python ../scripts/build_platform.py --write-manifest
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import timedelta
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from fastapi import HTTPException  # noqa: E402

from src.app.gate import scan  # noqa: E402
from src.app.pipeline import acceptance, cost, discover, generate, monitoring  # noqa: E402
from src.app.pipeline import reference as ref  # noqa: E402
from src.app.services import audit, changes  # noqa: E402
from src.settings import settings  # noqa: E402

MANIFEST = REPO_ROOT / "infra-azure" / "build.sha256"
SCHEMA = REPO_ROOT / "backend" / "src" / "app" / "pipeline" / "schema.sql"
UNPINNED = {"kv"}

# The fortnight before the demo's today, through the same rules as a click.
# (days before today, actor, action, args)
HISTORY = [
    (12, "Platform lead", "propose", ("my-first-app", "retire", None, "A tutorial project on a Pro plan; nobody has used it in 30 days.")),
    (11, "CAB - Head of Innovation", "decide", ("CR-001", True, "Agreed. Nothing depends on it.")),
    (11, "Platform lead", "implement", ("CR-001",)),
    (10, "Builder - Ella R.", "propose", ("listing-copy", "migrate", None, "First tool into the Place organisation; no personal data, many users.")),
    (9, "CAB - Business Systems", "decide", ("CR-002", True, "Agreed as the pilot migration.")),
    (8, "Platform lead", "implement", ("CR-002",)),
    (7, "Platform lead", "propose", ("appraisal-writer", "release", None, "Most-asked-for tool; the vendor-facing letters matter.")),
    (6, "CAB - MSP change manager", "decide", ("CR-003", True, "Fine by us.")),
    (6, "CAB - MSP change manager", "decide", ("CR-003", False, "Not yet: it is on personal accounts and the gate refuses it.")),
    (5, "Platform lead", "propose", ("lease-renewal", "transfer_owner", "sophie.q@staff.example", "The owner left in August; Sophie runs renewals at her office.")),
    (4, "Builder - Mia K.", "propose", ("appraisal-gen", "merge", "appraisal-writer", "Two appraisal tools; the writer has four times the users.")),
    (3, "CAB - Head of Innovation", "propose", ("referrals", "retire", None, "Owner left; nobody has used it in 30 days.")),
    (3, "CAB - Head of Innovation", "decide", ("CR-006", True, "Approving my own, it is obvious.")),
]


def table_digests(con: duckdb.DuckDBPyConnection) -> list[str]:
    lines = []
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY 1").fetchall()]
    for table in tables:
        if table in UNPINNED:
            continue
        digest = hashlib.sha256()
        for row in con.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall():
            digest.update(("\x1f".join("" if v is None else str(v) for v in row) + "\n").encode("utf-8"))
        lines.append(f"{digest.hexdigest()}  {table}")
    return lines


def _tool_id(con, key: str) -> str:
    t = next(t for t in ref.TOOLS if t["key"] == key) if key in ref.TOOL_KEYS else None
    if t:
        row = con.execute("SELECT tool_id FROM tool WHERE repo = ? OR agent_id = ? OR site = ? OR repo_candidates LIKE ?",
                          [t.get("repo"), t.get("agent_id"), t.get("site") or t.get("project"), f"%{t.get('repo')}%"]).fetchone()
    else:
        row = con.execute("SELECT tool_id FROM tool WHERE key = ? OR site = ?", [key, key]).fetchone()
    return row[0]


def history(con: duckdb.DuckDBPyConnection) -> tuple[int, int]:
    done = refused = 0
    for days, actor, action, args in HISTORY:
        audit.CLOCK = ref.DEMO_NOW - timedelta(days=days)
        try:
            if action == "propose":
                key, kind, target, reason = args
                tid = _tool_id(con, key)
                if kind == "merge":
                    target = _tool_id(con, target)
                changes.propose(con, actor, tid, kind, target, reason, at=audit.CLOCK)
            elif action == "decide":
                changes.decide(con, actor, args[0], args[1], args[2], at=audit.CLOCK)
            else:
                changes.implement(con, actor, args[0], at=audit.CLOCK)
            done += 1
        except HTTPException:
            refused += 1
    audit.CLOCK = None
    return done, refused


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    t0 = time.perf_counter()

    db_path = Path(settings.build_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for stale in (db_path, db_path.with_name(db_path.name + ".wal")):
        stale.unlink(missing_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA.read_text(encoding="utf-8"))

    print("1/8 landing the raw exports")
    generate.generate(con)
    print("    " + ", ".join(f"{t} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}" for t in
                             ("src_staff", "src_survey", "src_github_repos", "src_netlify_sites", "src_firebase_projects",
                              "src_supabase_projects", "src_copilot_agents", "src_billing", "src_expenses")))

    print("2/8 joining them into one register")
    found = discover.run(con)
    discover.ai_register(con)
    print(f"    {found['tools']} tools, {found['holds']} held, {found['dangling_dns']} dangling DNS records")

    print("3/8 the production gate")
    outcomes = scan.scan_all(con, ref.EXPORTS_TAKEN)
    scan.ablation(con)
    print(f"    {outcomes['pass']} pass, {outcomes['hold']} held for a person, {outcomes['refuse']} refused")

    print("4/8 cost")
    c = cost.run(con)
    print(f"    {c['lines']} cost lines, {c['unmatched_claims']} claims held")

    print("5/8 monitoring")
    monitoring.generate(con)
    m = monitoring.run(con)
    print(f"    {m['alerts']} alerts became {m['pages']} pages")

    print("6/8 the change history")
    done, refused = history(con)
    print(f"    {done} steps recorded, {refused} refused by the rules (and audit-logged)")

    print("7/8 acceptance checks")
    failed = [(name, detail) for name, ok, detail in acceptance.run(con) if not ok]
    if failed:
        for name, detail in failed:
            print(f"    FAILED {name}: {detail}", file=sys.stderr)
        return 1
    print(f"    all {len(acceptance.CHECKS)} pass")

    print("8/8 manifest")
    lines = table_digests(con)
    con.execute("INSERT INTO kv VALUES ('build_seconds', ?), ('git_sha', ?)",
                [f"{time.perf_counter() - t0:.1f}", settings.git_sha or "dev"])
    con.close()
    body = "\n".join(lines) + "\n"
    if args.write_manifest or not MANIFEST.exists():
        MANIFEST.write_text("# SHA-256 of every table the build produces.\n"
                            "# Regenerate with: uv run python ../scripts/build_platform.py --write-manifest\n" + body,
                            encoding="utf-8", newline="\n")
        print(f"    manifest written: {len(lines)} tables")
    else:
        pinned = [ln for ln in MANIFEST.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
        if sorted(pinned) != sorted(lines):
            changed = sorted(set(lines) ^ set(pinned))
            print(f"    MISMATCH against the pinned manifest in: {sorted({ln.split('  ')[1] for ln in changed})}", file=sys.stderr)
            return 1
        print(f"    verified: {len(lines)} tables match the pinned manifest")

    from src.app.services.db import copy_build
    copy_build()
    print(f"done in {time.perf_counter() - t0:.1f} s -> {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
