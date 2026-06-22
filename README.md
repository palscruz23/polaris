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

## Sample Demo

![Open Reliability Demo](demo.gif)

## Reliability Agent

The Reliability Agent is available at `/features/reliability-agent-team`.

Capabilities:

- Persistent reliability conversations that retain context across follow-up
  questions and planning sessions.
- Conversation history panel to review and switch between past reliability
  discussions.
- Automatic session titles summarised from the first reliability question.
- Conversation memory that carries forward key reliability context.
- Specialist selection and coordination — the Reliability Agent chooses which
  specialists to call, suppresses duplicate analysis, and limits to five
  specialist calls before synthesising a final response.
- Live progress updates while the agent coordinates specialist analysis.

Specialists:

- **Master Data Agent** — equipment discovery with text search, asset filters,
  and paginated match summaries.
- **Defect Elimination Agent** — bad actor ranking, repeat failure detection,
  reliability summary metrics, MTBF calculation, RCA evidence planning, 5 Whys
  generation, RCA template construction, defect elimination charter generation,
  and prioritised recommendations.
- **Maintenance Strategy Agent** — maintenance task profile review, maintenance
  mix breakdown, failure-mode coverage analysis, frequency risk assessment,
  strategy gap identification, condition-monitoring opportunity review, and
  evidence-backed recommendations.
- **Reliability Improvement Agent** — planned value, action-plan, reporting, and
  roadmap workflow.

## Workflow and Tooling

The Reliability Agent coordinates specialists through deterministic tools.
Available tools by agent:

### Reliability Agent tools

- `SpecialistRouter` — Selects the right specialist for the request.
- `BoundedSpecialistLoop` — Runs up to five sequential specialist calls.
- `DuplicateCallSuppressor` — Blocks repeated specialist calls.
- `ProgressStreamer` — Streams coordination status to the UI.
- `MemoryUpdater` — Saves useful context for follow-up questions.

### Master Data Agent tools

- `EquipmentSearch` — Finds equipment by keyword and asset filters.
- `PaginatedMatchSummaries` — Pages large equipment result sets.

### Defect Elimination Agent tools

- `ReliabilityMetricsTool` — Summarises failures, downtime, and cost.
- `BadActorAnalysisTool` — Ranks assets by reliability impact.
- `RepeatFailureDetectionTool` — Finds recurring asset/failure-mode pairs.
- `MTBFCalculator` — Estimates mean time between failures.
- `RCAEvidencePlanningTool` — Lists evidence needed for RCA.
- `FiveWhysGeneratorTool` — Drafts 5 Whys prompts.
- `RCATemplateBuilderTool` — Builds RCA worksheets.
- `DefectEliminationCharterGeneratorTool` — Creates defect elimination charters.
- `PrioritisedRecommendations` — Recommends evidence-backed next actions.

### Maintenance Strategy Agent tools

- `TaskProfileReviewer` — Summarises planned maintenance tasks.
- `MaintenanceMixBreakdown` — Groups tasks by maintenance type.
- `FailureModeCoverageAnalyzer` — Shows covered and uncovered risks.
- `FrequencyRiskAssessor` — Flags interval risk.
- `StrategyGapIdentifier` — Finds missing or duplicated controls.
- `ConditionMonitoringReviewer` — Identifies PdM/CBM opportunities.
- `StrategyRecommendationEngine` — Recommends strategy changes.

### Reliability Improvement Agent tools

- `ValueWorkflow` — Quantifies expected opportunity value.
- `ActionPlanWorkflow` — Converts opportunities into delivery plans.
- `ReportingWorkflow` — Tracks benefits and reliability outcomes.
- `RoadmapWorkflow` — Sequences improvement initiatives.

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

## Apps

- `apps/web` — Next.js frontend.
- `apps/api` — FastAPI backend for conversations, message persistence, memory updates, and model-provider access.

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
