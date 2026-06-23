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

[Open Reliability Webpage](https://open-reliability.vercel.app)

## Sample Demo

![Open Reliability Demo](demo.gif)

## Reliability Agent

The Reliability Agent is available at `/chat-with-reliability`.

Capabilities:

- Persistent reliability conversations that retain context across follow-up
  questions and planning sessions.
- Conversation history panel to review and switch between past reliability
  discussions.
- Automatic session titles summarised from the first reliability question.
- Conversation memory that carries forward key reliability context.
- Per-message model selection across approved OpenRouter models, with
  higher-cost GPT and Claude options reserved for production use.
- Specialist selection and coordination — the Reliability Agent chooses which
  specialists to call, suppresses duplicate analysis, and limits to five
  specialist calls before synthesising a final response.
- Live progress updates while the agent coordinates specialist analysis.

Specialists:

- **Master Data Agent** — equipment discovery with text search, asset filters,
  and paginated match summaries.
- **Defect Elimination Agent** — bad actor ranking, repeat failure detection,
  reliability summary metrics, MTBF calculation, Weibull analysis, RCA
  evidence planning, 5 Whys
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

- `SpecialistRouter` — selects the best specialist.
- `MultiCallCoordinator` — runs up to five specialist calls.
- `DuplicateCallGuard` — prevents repeated specialist calls.
- `ProgressStreamer` — streams live analysis progress.
- `ConversationMemoryUpdater` — saves context for follow-up questions.

### Master Data Agent tools

- `EquipmentSearch` — finds equipment using asset filters.
- `EquipmentMatchSummary` — returns paginated matches and counts.

### Defect Elimination Agent tools

- `ReliabilityMetricsCalculator` — summarizes reliability performance.
- `BadActorAnalyzer` — ranks high-impact equipment.
- `RepeatFailureDetector` — finds recurring failure patterns.
- `MTBFCalculator` — calculates mean time between failures.
- `WeibullAnalyzer` — estimates failure behavior and life distribution.
- `RCAEvidencePlanner` — identifies evidence needed for RCA.
- `FiveWhysGenerator` — drafts a structured 5 Whys analysis.
- `RCATemplateBuilder` — creates an RCA investigation worksheet.
- `DefectEliminationCharterBuilder` — creates an improvement charter.
- `RecommendationPrioritizer` — recommends evidence-backed next actions.

### Maintenance Strategy Agent tools

- `MaintenanceTaskProfiler` — summarizes planned maintenance tasks.
- `MaintenanceMixAnalyzer` — groups tasks by maintenance type.
- `FailureModeCoverageAnalyzer` — finds covered and uncovered risks.
- `FrequencyRiskAssessor` — flags weak maintenance intervals.
- `StrategyGapDetector` — identifies missing or duplicated controls.
- `ConditionMonitoringAdvisor` — finds PdM and CBM opportunities.
- `StrategyRecommender` — recommends evidence-backed strategy changes.

### Reliability Improvement Agent tools

- `ValueEstimator` — Future: quantifies expected improvement value.
- `ActionPlanBuilder` — Future: creates owners, milestones, and deliverables.
- `OutcomeReporter` — Future: tracks benefits and reliability outcomes.
- `RoadmapPlanner` — Future: sequences reliability initiatives.

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

Update `apps/api/.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_SITE_URL=http://localhost:3000
OPENROUTER_APP_NAME=Open Reliability
FRONTEND_URL=http://localhost:3000

DATABASE_URL=postgresql+psycopg://user:password@host:5432/open_reliability
```

The OpenRouter key is used only by the backend. Never place it in
`apps/web/.env.local`, expose it through a `NEXT_PUBLIC_*` variable, or commit
the real key to Git.

Restart or reload Uvicorn after changing `apps/api/.env`, because environment
settings are loaded when the backend starts.

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
http://localhost:3000/chat-with-reliability
```

For production, configure `OPENROUTER_API_KEY` and `DATABASE_URL` through the
hosting platform's encrypted backend secrets rather than a deployed `.env`
file.

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


## License

Open Reliability is licensed under the
[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution information.
