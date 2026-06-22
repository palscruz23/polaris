# Open Reliability

Open Reliability is a reliability-engineering assistant workspace. The current
app ships a Reliability Agent chat experience for asking maintenance, asset
reliability, and defect-elimination questions, backed by persistent
conversations, message history, model-provider access, and conversation memory
updates.

The broader product vision is a planned multi-agent reliability platform with
Master Data, Defect Elimination, Strategy, and Reliability Improvement agents.
Until those specialist workflows are implemented, they should be described as
planned capability rather than live backend behavior.

## Apps

- `apps/web` — Next.js frontend.
- `apps/api` — FastAPI backend for conversations, message persistence, memory updates, and model-provider access.

## Current Reliability Agent

The Reliability Agent lives at:

```text
/features/reliability-agent-team
```

Current chat capabilities:

- Persistent conversations stored by the API.
- A left-side conversation history panel inspired by ChatGPT.
- Recent conversations ordered by most recently updated.
- Summarised session titles generated from the first user message.
- Returning to the latest active conversation via browser local storage.
- Conversation memory updates so follow-up questions retain useful context.

Current backend capabilities:

- `GET /health` service status.
- `POST /conversations` conversation creation.
- `GET /conversations` recent conversation listing.
- `GET /conversations/{conversation_id}` conversation retrieval.
- `POST /conversations/{conversation_id}/messages` user-message persistence,
  provider-backed assistant response generation, and memory updates.
- Reliability data model tables for equipment, work orders, maintenance
  strategies, failure modes, import batches, and validation results.
- Clean reliability seed loader for loading MVP-ready CSV data into the
  normalized reliability model.
- Defect Elimination Agent foundation with deterministic tools for bad actor
  analysis, repeat failure detection, reliability summary metrics, MTBF
  calculation, RCA evidence planning, 5 Whys generation, RCA template building,
  defect elimination charter generation, and recommendations.

Current defect elimination endpoint:

- `GET /defect-elimination/overview` returns dataset summary, ranked bad
  actors, repeat failure groups, MTBF metrics, RCA evidence plans, 5 Whys
  prompts, RCA templates, defect elimination charters, and recommended next
  actions.

## Clean reliability seed data

The MVP assumes clean source data. To load the included sample reliability
dataset, start Postgres, run migrations, then run the seed loader:

```bash
docker compose up -d postgres
cd apps/api
./.venv/bin/alembic upgrade head
./.venv/bin/python -m app.cli.seed_reliability_data sample_data/reliability
```

The seed directory expects these CSV files:

```text
equipment.csv
failure_modes.csv
maintenance_strategies.csv
work_orders.csv
work_order_failure_modes.csv
```

The final failure-mode link file is optional, but the other four are required.
Rows are treated as clean data: missing required references raise an error
instead of being guessed or repaired.

The included sample dataset contains 50 equipment records, 100 maintenance
strategy tasks, 1,000 work orders across 2023-2025, and failure-mode links for
corrective, emergency, and condition-monitoring work orders.

## Agent Naming

Use this naming scheme across product copy, docs, and workflows:

- `Reliability Agent` - the only user-visible chat agent and future
  orchestrator.
- `Master Data Agent` - planned upload, mapping, validation, and data-readiness
  workflow.
- `Defect Elimination Agent` - planned repeat-failure and RCA workflow.
- `Strategy Agent` - planned PM strategy and failure-mode coverage workflow.
- `Reliability Improvement Agent` - planned value, action-plan, reporting, and
  roadmap workflow.

Example title behavior:

```text
First message:
Can you help me troubleshoot repeated failures on pump P-101?

History title:
Troubleshoot Repeated Failures Pump P-101
```

The title summariser is deterministic rather than model-generated. This keeps session creation fast and avoids spending model tokens just to name a chat.

## Local setup

### API

```bash
cd apps/api
cp .env.example .env
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/alembic upgrade head
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Update `apps/api/.env` with your database URL and model provider key.

### Web

```bash
cd apps/web
npm install
npm run dev
```

The frontend expects:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Open the app at:

```text
http://localhost:3000
```

## Useful checks

API:

```bash
cd apps/api
./.venv/bin/python -m pytest
./.venv/bin/python -m compileall app tests
```

Web:

```bash
cd apps/web
npm run lint
npm run build
```

## Notes for contributors

- Keep feature work incremental.
- Preserve existing user changes in the working tree.
- Do not commit real secrets from `.env` files.
- Recommended future enhancement: add rename/delete controls for conversation history.
