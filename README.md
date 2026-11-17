# Place technology platform (demo)

> Built for a job application. **Not affiliated with or endorsed by Place Estate Agents.**
> All data - tools, people, code, bills, alerts - is synthetic. The logo, favicon and
> colours are Place's own public ones (from eplace.com.au), used to show the work in
> Place's context.

Staff have built useful tools with Claude and Copilot Studio, on Supabase, Firebase,
Netlify and personal GitHub. This is the platform a technology platform lead would
stand up to bring them in without stopping anyone building, laid out as the
advertisement's first ninety days.

| | What it does |
|---|---|
| **Tool register** | Ten exports - HR feed, survey, GitHub, Netlify, Firebase, Supabase, Copilot Studio, DNS, billing, expense claims - joined into one register by the keys they share, never by name. Owners who have left, tools nobody declared, DNS names that point at nothing. What the evidence cannot decide is held for a person. |
| **AI register** | Every route to a model in use, from the evidence: personal subscriptions on expense claims, model SDKs in the code, Copilot Studio agents. Checked against the policy's approved routes. |
| **Production gate** | Eleven checks aimed at what AI-written pilot code gets wrong - keys in code and history, service-role keys in the browser, rules opened during testing, SQL from input, functions that answer anyone, made-up packages, personal data to a model on a personal key. Refuse or hold, never warn. Each check priced by ablation. A fix branch per defect; a removed key refuses until its rotation is recorded. |
| **Changes** | Migrate, release, merge, retire, transfer: evidence attached by the server, decided by a CAB member who did not propose it, implemented by the platform lead, every rule checked again at implementation. Refusals audit-logged. |
| **Paved road** | The template every tool moves into: the gate, dependency review and CodeQL in CI, CODEOWNERS, Dependabot, a branch ruleset, a register entry, a Terraform module. |
| **Monitoring** | Four weeks of alerts from ten tools through six noise rules: 766 alerts to 9 pages, all seven incidents still paged. Each rule switched off, and the rejected alternatives kept with what they would have missed. Straight-line forecasts for limits and certificates. |
| **Incident triage** | An agent with six read-only tools over a masked snapshot proposes a cause and action; graded against the runbook on real, renamed, hard and adversarial cases. |
| **Cloud cost** | Five platforms' bills and the claims that pay them, attributed to tools; idle, oversized, duplicate, drifted; tools billed to a leaver's card; a labelled planning figure for consolidation. |
| **CAB report** | Assembled from the data on request: decisions wanted, changes, refusals, risks due, cost. |

## How it is built

- **Backend**: FastAPI, Python 3.12, DuckDB. Integer arithmetic for money.
- **Frontend**: React 18 + Vite, Recharts.
- **Data**: generated from a seed at image build, with every defect declared once in
  `backend/src/app/pipeline/reference.py`. The tests check each is found from the data.
  The build runs acceptance checks and verifies every table against
  `infra-azure/build.sha256`; an image that cannot reproduce it is never published.
- **The gate runs on this repository** in CI, with its exemptions listed in `.gateignore`.
- **Azure**: one Container App (nginx + FastAPI sidecar), consumption plan, warm in
  Brisbane business hours and at zero outside them, public images on GHCR, no registry,
  no vault, no database server, a budget tripwire.

## Run it

```bash
cd backend && uv sync && uv run python ../scripts/build_platform.py && uv run uvicorn src.main:app --port 8071
cd frontend && npm install && npm run dev        # http://localhost:5271
```

`cd backend && uv run pytest` for the tests; `node frontend/evals/check-pages.mjs` renders
every page on desktop and phone; `TOKEN=... node frontend/evals/flow.mjs` drives the
write path; `uv run python -m src.app.gate.cli <folder>` runs the gate on any folder;
`uv run python ../evals/run_triage_eval.py` grades the agent (needs a model key in `.env`).

The public link is an open demo: any visitor can propose, decide and implement changes,
acting as any of the demo roles, under a per-address write limit. The rules still refuse
- nobody decides their own change - and every refusal is audit-logged. Changes live in a
working copy that returns to the build on every cold start; resetting on demand needs the
operator's token, which is never published.
