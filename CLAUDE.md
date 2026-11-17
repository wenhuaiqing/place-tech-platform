# place-tech-platform

Portfolio demo: a reporting site for a 26-office residential real estate agency - sales,
rentals, offices, marketing, data checks, and a data agent on every page - built the way a
platform lead would want staff-built tools built. For an application to Place Estate
Agents (Technology Platform Lead) and named for it. **Not affiliated with or endorsed by
Place. All data is synthetic.**

## Layout

```
place-tech-platform/
├── backend/           FastAPI + Python 3.12 (uv)
│   └── src/app/
│       ├── pipeline/  reference (assumptions, seeded errors), schema.sql, generate, checks,
│       │              views.sql, acceptance
│       ├── services/  agents/ (planner, data_query, general, summariser), catalogue,
│       │              sql_validator, llm, db, auth, audit, rate_limit
│       └── routers/   reports (every page), orb (the assistant, SSE)
├── scripts/           build_platform.py - everything from nothing
├── evals/             run_agent_eval.py -> status.json (shown on Ask the data)
├── frontend/          React 18 + Vite; pages/<Section>/<Page>.jsx auto-discovered
└── infra-azure/       Terraform; build.sha256 is the pinned manifest
```

## How to run

```bash
cd backend && uv sync && uv run python ../scripts/build_platform.py && uv run uvicorn src.main:app --port 8071
cd frontend && npm install && npm run dev     # :5271
```

Tests: `cd backend && uv run pytest`. Pages: `cd frontend && node evals/check-pages.mjs`.
Reader's path: `node evals/flow.mjs`.

## Conventions

- **No emojis in code or output.** Australian English; dates DD/MM/YYYY on screen;
  straight quotes and hyphens only (the page check fails on typographic ones).
- **Personal identity only.** No employer name, work e-mail, work machine path, internal
  system or real data from any employer appears in this repository.
- Every seeded error is declared once in `pipeline/reference.py`; the checks never read
  `truth_defect`, and the tests compare what they found with it.
- Reports read only the `v_*` views, which leave quarantined records out once, so no page
  can forget to. No personal details about tenants, vendors or buyers exist in the data.
- The data agent reads only the `v_*` views through the SQL gate, on a connection with
  external access off. It cannot write. Numbers on screen come from the data; assumptions
  (commission range, bond lodgement window, arrears threshold) are labelled where used.
- Changing the generator, checks or views changes the output: rebuild with
  `--write-manifest` and commit `infra-azure/build.sha256`, or CI and the image build fail.
- Azure: one resource group, scale to zero, no registry, no vault, no database.
- Named for the business it was built for, and says so: the not-affiliated line stays in
  the sidebar, the First 90 days page and the README. It uses Place's public logo and
  colours (navy #090A39, teal #128190, from eplace.com.au). Nothing claims to know Place's
  offices, results or systems.
