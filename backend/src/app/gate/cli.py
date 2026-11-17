"""Run the production gate over a folder, as a repository's CI does.

  python -m src.app.gate.cli <path> [--personal]

Exit code 0 when the gate passes, 2 when it holds (a person must look),
1 when it refuses. --personal says the tool holds personal information, which
makes some checks refuse rather than hold. The paved-road workflow
(paved-road/.github/workflows/gate.yml) runs this on every pull request.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.app.gate import rules

SKIP = {".git", "node_modules", ".venv", "dist", "__pycache__", "data", ".terraform"}
TEXT = {".js", ".jsx", ".ts", ".tsx", ".py", ".json", ".toml", ".sql", ".rules", ".env", ".yml", ".yaml", ".md", ".txt"}


def exemptions(root: Path) -> dict[str, str]:
    f = root / ".gateignore"
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            path, _, why = line.partition("#")
            if path.strip():
                out[path.strip()] = why.strip()
    return out


def collect(root: Path, exempt: dict[str, str]) -> list[tuple[str, str, bool]]:
    files = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP for part in p.relative_to(root).parts):
            continue
        rel = p.relative_to(root).as_posix()
        if any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in exempt):
            continue
        if p.suffix not in TEXT and p.name not in ("firestore.rules", "storage.rules", ".env", ".firebaserc"):
            continue
        try:
            files.append((p.relative_to(root).as_posix(), p.read_text(encoding="utf-8"), True))
        except (UnicodeDecodeError, OSError):
            continue
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--personal", action="store_true", help="the tool holds personal information")
    args = parser.parse_args()
    root = Path(args.path)
    exempt = exemptions(root)
    for path, why in exempt.items():
        print(f"EXEMPT  {path}  ({why})")
    files = collect(root, exempt)
    findings = rules.scan(files, rules.Context(data_classes={"personal"} if args.personal else {"internal"}))
    for f in findings:
        print(f"{f.outcome.upper():7s} {f.rule_id} {f.path}:{f.line}  {rules.RULES[f.rule_id][0]}: {f.evidence}")
        print(f"        {f.detail}")
    result = rules.outcome(findings)
    print(f"\n{len(files)} files scanned; gate: {result}")
    return {"pass": 0, "hold": 2, "refuse": 1}[result]


if __name__ == "__main__":
    sys.exit(main())
