# Place business reporting (demo)

> Built for a job application. **Not affiliated with or endorsed by Place Estate Agents.**
> All data - offices, people, properties, sales, tenancies - is synthetic. The 26 offices
> are from the advertisement; nothing else describes Place. The logo, favicon and colours
> are Place's own public ones (from eplace.com.au), used to show the work in Place's context.

A reporting site for a 26-office residential agency, of the kind the advertisement says
staff are building with Claude and Copilot Studio - built the way a platform lead would
want every such tool built.

| | What it shows |
|---|---|
| **Overview** | Sales, commission, days on market, auction clearance, the rent roll, arrears, renewals and urgent repairs - this financial year against the same days last year. |
| **Sales** | Appraisal to listing to contract to settlement for the group or one office; the settlement pipeline; agents. |
| **Rentals** | The rent roll, weekly arrears and the watch list, vacancies, leases ending, maintenance, bonds lodged late. Tenancies by number only - no personal details anywhere. |
| **Offices** | All 26 on one scorecard, linked through to each office's sales. |
| **Marketing** | Vendor-paid advertising against budget, and enquiries by channel. |
| **Data checks** | Seven checks find the data-entry errors before a report counts them; what fails is listed and kept out of the figures. |
| **Ask the data** | An assistant on every page: plain English to one SQL query, checked by a gate, run read-only, answered with the query behind it. Graded on answerable, unanswerable and adversarial questions. |
| **How it is run** | The path to production every staff-built tool should take - and this one did. |

## How it is built

- **Backend**: FastAPI, Python 3.12, DuckDB. Money in cents; integer draws, so the data
  is byte-identical on any machine.
- **Assistant**: the agent layer from my earlier real estate demo (planner -> data
  agent -> summariser on LangGraph, streamed over SSE), moved to Azure and the OpenAI
  protocol (Gemini on this deployment; any provider by configuration).
- **Frontend**: React 18 + Vite, Recharts.
- **Data**: generated from a seed at image build, with every seeded error declared once
  in `backend/src/app/pipeline/reference.py`; the tests check each is found from the data.
  The build runs acceptance checks and verifies every table against
  `infra-azure/build.sha256` - an image that cannot reproduce it is never published.
- **Azure**: one Container App (nginx + FastAPI sidecar), consumption plan, warm in
  Brisbane business hours and at zero outside them, public images on GHCR, no registry,
  no vault, no database server, a budget tripwire.

## Run it

```bash
cd backend && uv sync && uv run python ../scripts/build_platform.py && uv run uvicorn src.main:app --port 8071
cd frontend && npm install && npm run dev        # http://localhost:5271
```

`cd backend && uv run pytest` for the tests; `node frontend/evals/check-pages.mjs` renders
every page on desktop and phone; `node frontend/evals/flow.mjs` drives a reader's path
including the assistant; `uv run python ../evals/run_agent_eval.py` grades the agent
(needs a model key in `.env`).
