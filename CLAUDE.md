# place-tech-platform

Portfolio demo: the platform a technology platform lead would stand up to bring
staff-built AI tools under control - a register joined from ten exports, a production
gate for AI-written code, CAB-governed changes, a paved road, monitoring with noise rules
and a graded triage agent, cost, and a CAB report. Built for an application to Place
Estate Agents (Technology Platform Lead) and named for it. **Not affiliated with or
endorsed by Place. All data is synthetic.**

## Layout

```
place-tech-platform/
├── backend/           FastAPI + Python 3.12 (uv)
│   └── src/app/
│       ├── pipeline/  reference (every assumption and seeded defect), schema.sql, generate,
│       │              code (the synthetic repositories), discover, cost, monitoring, acceptance
│       ├── gate/      rules (the checks), scan (per tool + ablation), cli (for CI)
│       ├── services/  changes (governed writes), triage, triage_cases, llm, audit, auth, db, rate_limit
│       └── routers/   platform, register, operations
├── paved-road/        the template every tool moves into (served on the Paved road page)
├── scripts/           build_platform.py - everything from nothing
├── evals/             run_triage_eval.py -> status.json (shown on the Incident triage page)
├── frontend/          React 18 + Vite; pages/<Section>/<Page>.jsx auto-discovered
└── infra-azure/       Terraform; build.sha256 is the pinned manifest
```

## How to run

```bash
cd backend && uv sync && uv run python ../scripts/build_platform.py && uv run uvicorn src.main:app --port 8071
cd frontend && npm install && npm run dev     # :5271
```

Tests: `cd backend && uv run pytest`. Pages: `cd frontend && node evals/check-pages.mjs`.
Write path: `TOKEN=<DEMO_WRITE_TOKEN> node evals/flow.mjs`. Gate on this repo:
`cd backend && uv run python -m src.app.gate.cli ..`.

## Conventions

- **No emojis in code or output.** Australian English; dates DD/MM/YYYY on screen;
  straight quotes and hyphens only (the page check fails on typographic ones).
- **Personal identity only.** Commits, CI, registry, README and infrastructure use the
  author's personal accounts. No employer name, work e-mail, work machine path, internal
  system or real data from any employer appears in this repository.
- Every defect the generator seeds is declared once in `pipeline/reference.py`; tests
  assert each is found from the data, never from the reference.
- Hold, never guess: discovery holds conflicting evidence for a person; nothing in an
  export is dropped without a tool or a hold (the build checks).
- The gate decides from the code. Nothing is marked fixed by hand: a fix is new code and
  a re-scan, and a removed secret needs a recorded rotation.
- Every write goes through `auth.require_write`, is audit-logged, and is refused - not
  warned - when the rule says no. Nobody decides their own change; only the platform
  lead implements; rules are re-checked at implementation.
- The triage agent reads only masked snapshots and cannot write. Numbers on screen come
  from the data; assumptions (exchange rate, planning figures, tiers, the AI gateway) are
  labelled where they are used.
- Changing the generator, pipeline or rules changes the output: rebuild with
  `--write-manifest` and commit `infra-azure/build.sha256`, or CI and the image build fail.
- Azure: one resource group, scale to zero, no registry, no vault, no database.
- Named for the business it was built for, and says so: the not-affiliated line stays in
  the sidebar, the First 90 days page and the README. It uses Place's public logo and
  colours (navy #090A39, teal #128190, from eplace.com.au), so that line must never be
  removed or made less visible. Nothing claims to know how Place operates.
