# Open Reliability

Open Reliability is a reliability-engineering assistant workspace. The current
app ships a Reliability Agent chat experience for asking maintenance, asset
reliability, and defect-elimination questions, backed by persistent
conversations, message history, model-provider access, and conversation memory
updates. The Reliability Agent can select and execute registered specialist
capabilities through a bounded sequential multi-call loop.

The Master Data, Defect Elimination, and Maintenance Strategy agents are
implemented specialists in the broader multi-agent vision. Reliability
Improvement remains planned.

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
- Model-selected specialist execution with duplicate-call suppression and a
  five-call limit before final response synthesis.
- Live natural-language progress while the Reliability Agent coordinates
  specialists and their deterministic analysis tools.

Current backend capabilities:

- `GET /health` service status.
- `POST /conversations` conversation creation.
- `GET /conversations` recent conversation listing.
- `GET /conversations/{conversation_id}` conversation retrieval.
- `POST /conversations/{conversation_id}/messages` user-message persistence,
  provider-backed assistant response generation, and memory updates.
- `POST /conversations/{conversation_id}/messages/stream` emits NDJSON
  orchestration progress followed by the persisted message exchange.
- Reliability data model tables for equipment, work orders, maintenance
  strategies, failure modes, import batches, and validation results.
- Master Data Agent equipment discovery with text search, asset filters,
  pagination, and matching equipment summary counts.
- Clean reliability seed loader for loading MVP-ready CSV data into the
  normalized reliability model.
- Defect Elimination Agent with deterministic tools for bad actor
  analysis, repeat failure detection, reliability summary metrics, MTBF
  calculation, RCA evidence planning, 5 Whys generation, RCA template building,
  defect elimination charter generation, and recommendations.
- Reliability Agent orchestration of Defect Elimination findings into the
  user-facing chat response.
- Maintenance Strategy Agent review of maintenance task profiles, maintenance
  mix, observed failure-mode coverage, frequency risks, strategy gaps,
  condition-monitoring opportunities, and evidence-backed recommendations.

Current defect elimination endpoint:

- `GET /defect-elimination/overview` returns dataset summary, ranked bad
  actors, repeat failure groups, MTBF metrics, RCA evidence plans, 5 Whys
  prompts, RCA templates, defect elimination charters, and recommended next
  actions.

## Workflow and Tooling

The Reliability Agent coordinates specialists through deterministic tools:

### Master Data tools
- Equipment search by keyword, asset tags, and facility filters.
- Paginated results with match-count summaries.

### Defect Elimination tools
- Bad actor ranking by failure count and downtime hours.
- Repeat failure detection across time windows.
- Reliability summary metrics (asset-level and system-level).
- MTBF calculation from work order history.
- 5 Whys generation for failure mode investigation.
- RCA template construction with evidence planning.
- Defect elimination charter generation.
- Prioritised recommendations with supporting evidence.

### Maintenance Strategy tools
- Maintenance task profile review by equipment context.
- Maintenance mix breakdown (PM, PdM, CBM, corrective, run-to-failure).
- Failure-mode coverage analysis against known failure modes.
- Frequency risk assessment for scheduled maintenance tasks.
- Strategy gap identification and condition-monitoring opportunity review.
- Evidence-backed strategy recommendations.

### Orchestration
- The Reliability Agent selects and calls specialist agents through a
  bounded multi-call loop (up to five calls per request).
- Duplicate-call suppression prevents redundant specialist invocations.
- Live natural-language progress is streamed to the frontend during
  coordination.

## Agent Naming

Use this naming scheme across product copy, docs, and workflows:

- `Reliability Agent` - the only user-visible chat agent and orchestrator.
- `Master Data Agent` - implemented equipment discovery; upload, mapping,
  validation, and data-readiness workflows remain planned.
- `Defect Elimination Agent` - implemented repeat-failure and RCA workflow.
- `Maintenance Strategy Agent` - implemented maintenance strategy and
  failure-mode coverage workflow.
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
