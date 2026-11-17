"""Run the triage eval: every labelled case through the runbook and the agent,
graded the same way. Writes evals/status.json, which the Incident triage page reads.

Usage (from backend/):
  uv run python ../evals/run_triage_eval.py                 # agent + runbook
  uv run python ../evals/run_triage_eval.py --retry-errors  # re-run only the cases the provider errored on
  uv run python ../evals/run_triage_eval.py --regrade       # re-grade stored runs with the current grader, no model calls
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from src.app.services import db, llm  # noqa: E402
from src.app.services.triage import grade, run_agent, run_rules  # noqa: E402
from src.app.services.triage_cases import build_cases  # noqa: E402
from src.settings import settings  # noqa: E402

OUT = REPO_ROOT / "evals" / "status.json"
KINDS = ("real", "variant", "hard", "adversarial")


def summarise(results: list[dict], engine: str) -> dict | None:
    rs = [r for r in results if r["engine"] == engine]
    ok = [r for r in rs if "grade" in r]
    if not rs:
        return None
    by_kind = {k: {"cases": sum(r["kind"] == k for r in ok), "passed": sum(r["grade"]["passed"] for r in ok if r["kind"] == k)} for k in KINDS}
    ms = [r["ms"] for r in ok]
    return {
        "cases": len(rs), "errors": len(rs) - len(ok),
        "passed": sum(r["grade"]["passed"] for r in ok),
        "category_ok": sum(r["grade"]["category_ok"] for r in ok),
        "harmful": sum(r["grade"]["harmful"] for r in ok),
        "abstained": sum(r["grade"]["abstained"] for r in ok),
        "evidence_grounded": sum(r["grade"]["grounded"] for r in ok),
        "evidence_items": sum(r["grade"]["evidence"] for r in ok),
        "by_kind": by_kind,
        "p50_ms": round(statistics.median(ms)) if ms else None,
        "p95_ms": round(sorted(ms)[int(0.95 * (len(ms) - 1))]) if ms else None,
        "avg_steps": round(statistics.mean(r["steps"] for r in ok), 2) if ok else None,
        "fallback_model_used": sum(1 for r in ok if r.get("model") not in (settings.llm_chat_model, "runbook")),
    }


def run_case(case: dict, engine: str) -> dict:
    entry = {"case_id": case["case_id"], "kind": case["kind"], "engine": engine, "label": case["label"], "why": case.get("why"),
             "summary": case["case"]["summary"]}
    fn = run_agent if engine == "agent" else run_rules
    try:
        run = fn(case["case"])
        entry.update({"result": run["result"], "model": run["model"], "ms": run["ms"], "steps": run["steps"],
                      "tools": [t["tool"] for t in run["trace"] if t.get("kind") == "tool"],
                      # Stored so a grader change can re-grade without new model calls.
                      "retrieved": run["retrieved"] if engine == "agent" else None,
                      "grade": grade(run, case["label"])})
    except Exception as exc:  # noqa: BLE001 - an error is a result, recorded as one
        entry.update({"error": f"{type(exc).__name__}: {str(exc)[:300]}", "ms": None, "steps": None})
    return entry


def write(status: dict) -> None:
    status["summary"] = {"rules": summarise(status["results"], "rules"), "agent": summarise(status["results"], "agent")}
    OUT.write_text(json.dumps(status, indent=1, default=str), encoding="utf-8", newline="\n")
    print(json.dumps(status["summary"], indent=1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pause", type=float, default=2.0, help="seconds between agent cases (free-tier pacing)")
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--regrade", action="store_true")
    args = parser.parse_args()
    cases = {c["case_id"]: c for c in build_cases(db.raw("SELECT * FROM incident_world ORDER BY incident_id"))}

    if args.regrade or args.retry_errors:
        status = json.loads(OUT.read_text(encoding="utf-8"))
        for i, r in enumerate(status["results"]):
            if args.regrade and r.get("engine") == "agent" and r.get("retrieved") is not None:
                r["grade"] = grade({"result": r["result"], "retrieved": r["retrieved"]}, r["label"])
            if args.retry_errors and r.get("error"):
                status["results"][i] = run_case(cases[r["case_id"]], r["engine"])
                print(f"retried {r['case_id']}: {'ok' if 'grade' in status['results'][i] else status['results'][i]['error']}", flush=True)
                time.sleep(args.pause)
        status["regraded_at"] = datetime.now().replace(microsecond=0).isoformat()
        write(status)
        return 0

    if not llm.configured():
        print("No model configured (LLM_BASE_URL / LLM_API_KEY). Refusing to write a status without the agent.", file=sys.stderr)
        return 1
    started = datetime.now().replace(microsecond=0)
    results = []
    for n, case in enumerate(cases.values(), start=1):
        results.append(run_case(case, "rules"))
        entry = run_case(case, "agent")
        results.append(entry)
        g = entry.get("grade", {})
        print(f"[{n:02d}/{len(cases)}] {case['case_id']:34s} {'PASS' if g.get('passed') else 'FAIL' if g else 'ERROR'} "
              f"{entry.get('result', {}).get('category', entry.get('error', '-'))[:60]} {entry.get('ms')} ms", flush=True)
        time.sleep(args.pause)
    write({"run_at": started.isoformat(), "finished_at": datetime.now().replace(microsecond=0).isoformat(),
           "model": settings.llm_chat_model, "fallback_model": settings.llm_fallback_model or None, "cases": len(cases), "results": results})
    return 0


if __name__ == "__main__":
    sys.exit(main())
