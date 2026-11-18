"""Build everything from nothing.

  1. generate the agency's data: offices, people, appraisals, listings, sales,
     tenancies, arrears, maintenance, bonds, marketing - and the seeded errors
  2. run the data checks; quarantine what no report may count
  3. create the reporting views
  4. acceptance checks - a build that fails one is not a build
  5. check every table against the digests pinned in infra-azure/build.sha256

Usage (from backend/):
  uv run python ../scripts/build_platform.py              # build, verify against the manifest
  uv run python ../scripts/build_platform.py --write-manifest
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from fastapi import HTTPException  # noqa: E402

from src.app.pipeline import acceptance, checks, generate  # noqa: E402
from src.app.pipeline import reference as ref  # noqa: E402
from src.app.services import audit, work_orders  # noqa: E402
from src.settings import settings  # noqa: E402

MANIFEST = REPO_ROOT / "infra-azure" / "build.sha256"
SCHEMA = REPO_ROOT / "backend" / "src" / "app" / "pipeline" / "schema.sql"
UNPINNED = {"kv"}

AV, JO, HEAD = "Property manager - Avery", "Property manager - Jordan", "Head of property management"
# The fortnight before today, through the same rules as a click. (days before today, actor, action, args)
# Tenancies are picked by position among the office's current ones: t0, t1, ...; "ended" is one that has ended.
HISTORY = [
    (13, AV, "raise", ("t0", "Plumbing", "routine", "Leaking kitchen mixer tap; plumber to replace the cartridge.", 320_00)),
    (12, AV, "complete", ("WO-0001", 320_00, "")),
    (12, AV, "raise", ("t1", "Electrical", "urgent", "No power to the kitchen circuit; electrician today.", 780_00)),
    (12, AV, "decide", ("WO-0002", True, "Urgent, I'll approve it.")),
    (12, JO, "decide", ("WO-0002", True, "Safety: no power to the kitchen. Approved.")),
    (10, AV, "complete", ("WO-0002", 850_00, "")),
    (9, JO, "raise", ("t2", "Roof and gutters", "routine", "Replace rusted gutter along the rear of the house; two quotes obtained.", 3_450_00)),
    (9, AV, "decide", ("WO-0003", True, "Looks reasonable to me.")),
    (8, HEAD, "decide", ("WO-0003", True, "Lower of two quotes; owner agreed by email.")),
    (7, AV, "raise", ("t3", "Garden", "routine", "Front garden overgrown; tidy before the routine inspection.", 1_200_00)),
    (6, HEAD, "decide", ("WO-0004", False, "The lease makes the garden the tenant's job; raise it with them at inspection.")),
    (5, JO, "raise", ("t4", "Locks and keys", "urgent", "Tenant locked out; locksmith attended after hours.", 260_00)),
    (5, JO, "complete", ("WO-0005", 410_00, "")),
    (5, JO, "complete", ("WO-0005", 410_00, "After-hours call-out fee on top of the quoted lock change.")),
    (4, AV, "raise", ("ended", "Appliance", "routine", "Dishwasher not draining.", 450_00)),
    (3, JO, "raise", ("t5", "Appliance", "routine", "Oven element failed; replace like for like.", 640_00)),
    (2, AV, "raise", ("t6", "General repairs", "routine", "Rotten deck boards at the back stairs; carpenter to replace.", 2_600_00)),
]


def work_order_history(con: duckdb.DuckDBPyConnection) -> tuple[int, int]:
    from datetime import timedelta
    current = [r[0] for r in con.execute(
        f"SELECT tenancy_id FROM tenancy WHERE office_code = '{ref.WO_OFFICE}' AND end_on IS NULL ORDER BY tenancy_id").fetchall()]
    ended = con.execute(f"SELECT tenancy_id FROM tenancy WHERE office_code = '{ref.WO_OFFICE}' AND end_on < DATE '{ref.TODAY}' - INTERVAL 30 DAY ORDER BY end_on DESC, tenancy_id LIMIT 1").fetchone()[0]
    done = refused = 0
    for days, actor, action, args in HISTORY:
        audit.CLOCK = datetime.combine(ref.TODAY, datetime.min.time()) + timedelta(hours=9) - timedelta(days=days)
        try:
            if action == "raise":
                slot, *rest = args
                tid = ended if slot == "ended" else current[int(slot[1:])]
                work_orders.raise_order(con, actor, tid, *rest, at=audit.CLOCK)
            elif action == "decide":
                work_orders.decide(con, actor, *args, at=audit.CLOCK)
            else:
                work_orders.complete(con, actor, *args, at=audit.CLOCK)
            done += 1
        except HTTPException:
            refused += 1
    audit.CLOCK = None
    return done, refused


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

    PIPE = REPO_ROOT / "backend" / "src" / "app" / "pipeline"
    con.execute(f"INSERT INTO kv VALUES ('today', '{ref.TODAY}')")

    print("1/5 generating the agency")
    print("    " + ", ".join(f"{k} {v:,}" for k, v in generate.generate(con).items()))

    print("2/5 data checks")
    found = checks.run(con)
    print("    " + ", ".join(f"{k} {v}" for k, v in found.items()))

    print("3/5 reporting views")
    con.execute((PIPE / "views.sql").read_text(encoding="utf-8"))

    print("    work orders: %d steps recorded, %d refused by the rules (and audit-logged)" % work_order_history(con))

    print("4/5 acceptance checks")
    failed = [(name, detail) for name, ok, detail in acceptance.run(con) if not ok]
    if failed:
        for name, detail in failed:
            print(f"    FAILED {name}: {detail}", file=sys.stderr)
        return 1
    print(f"    all {len(acceptance.CHECKS)} pass")

    print("5/5 manifest")
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
