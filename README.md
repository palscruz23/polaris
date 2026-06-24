# Open Reliability


Open Reliability is a reliability-engineering assistant workspace. The current
app ships a Reliability Agent chat experience for asking maintenance, asset
reliability, and defect-elimination questions, backed by persistent
conversations, message history, model-provider access, and conversation memory
updates. The Reliability Agent can select and execute registered specialist
capabilities through a bounded sequential multi-call loop.

The Master Data, Defect Elimination, Maintenance Strategy, and Reliability
Improvement agents are implemented specialists in the broader multi-agent
vision.

[Open Reliability Webpage](https://open-reliability.vercel.app)

## Sample Demo

![Open Reliability Demo](demo.gif)

## Reliability Agent Workflow and Tooling

The Reliability Agent coordinates specialists through deterministic tools and
orchestration components. Available tools and components by agent:

### Specialist routes and intents

The Reliability Agent exposes one route per specialist agent. For specialist
routes with an `intent` argument, the Reliability Agent should choose the
narrowest intent that satisfies the user request; the specialist then manages
the internal deterministic tools required for that intent.

| Specialist | Intent | Description | Tool Calls (in sequence) |
| --- | --- | --- | --- |
| Master Data Agent | n/a | Search or list stored equipment so the user can find asset identifiers before deeper analysis. | `EquipmentSearchTool` |
| Defect Elimination Agent | `overview` | Run the full defect-elimination overview across reliability summary, bad actors, repeats, MTBF, Weibull, RCA prep, charters, and recommendations. | `ReliabilityMetricsTool` -> `BadActorAnalysisTool` -> `RepeatFailureDetectionTool` -> `MTBFCalculationTool` -> `WeibullAnalysisTool` -> `RCAEvidencePlanningTool` -> `FiveWhysGeneratorTool` -> `RCATemplateBuilderTool` -> `DefectEliminationCharterGeneratorTool` -> recommendation synthesis |
| Defect Elimination Agent | `rank_bad_actors` | Rank high-impact equipment using corrective-like work history, downtime, cost, MTTR, and MTBF context. | `ReliabilityMetricsTool` -> `BadActorAnalysisTool` -> recommendation synthesis |
| Defect Elimination Agent | `find_repeat_failures` | Find repeated equipment/failure-mode patterns that meet the occurrence threshold. | `ReliabilityMetricsTool` -> `RepeatFailureDetectionTool` -> recommendation synthesis |
| Defect Elimination Agent | `calculate_mtbf` | Calculate asset-level MTBF from corrective and emergency repair events. | `ReliabilityMetricsTool` -> `MTBFCalculationTool` -> recommendation synthesis |
| Defect Elimination Agent | `analyze_weibull` | Estimate directional Weibull behavior where enough repair interval history exists. | `ReliabilityMetricsTool` -> `WeibullAnalysisTool` -> recommendation synthesis |
| Defect Elimination Agent | `prepare_rca` | Build RCA preparation outputs for repeat failures, including evidence plans, 5 Whys prompts, templates, and charters. | `ReliabilityMetricsTool` -> `RepeatFailureDetectionTool` -> `MTBFCalculationTool` -> `RCAEvidencePlanningTool` -> `FiveWhysGeneratorTool` -> `RCATemplateBuilderTool` -> `DefectEliminationCharterGeneratorTool` -> recommendation synthesis |
| Maintenance Strategy Agent | `full_strategy_review` | Run the full maintenance strategy review from profile through recommendations. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` -> `FailureModeCoverageAnalyzerTool` -> `FrequencyRiskAnalyzerTool` -> `MaintenanceStrategyGapDetectorTool` -> `ConditionMonitoringOpportunityAnalyzerTool` -> `MaintenanceStrategyRecommendationBuilderTool` |
| Maintenance Strategy Agent | `summarize_strategy_profile` | Summarize existing maintenance strategy tasks, active task counts, types, frequencies, and statuses. | `MaintenanceStrategyProfileBuilderTool` |
| Maintenance Strategy Agent | `maintenance_mix` | Summarize preventive, inspection, condition-monitoring, corrective, and emergency work-order mix. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` |
| Maintenance Strategy Agent | `check_coverage` | Compare observed failure modes with active strategy task descriptions to classify coverage. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` -> `FailureModeCoverageAnalyzerTool` |
| Maintenance Strategy Agent | `assess_frequency` | Compare task intervals with observed repeat-failure recurrence to flag engineering-review risks. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` -> `FailureModeCoverageAnalyzerTool` -> `FrequencyRiskAnalyzerTool` |
| Maintenance Strategy Agent | `detect_gaps` | Identify missing active strategies, uncovered failure modes, and recurring partial-coverage gaps. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` -> `FailureModeCoverageAnalyzerTool` -> `FrequencyRiskAnalyzerTool` -> `MaintenanceStrategyGapDetectorTool` |
| Maintenance Strategy Agent | `find_monitoring_opportunities` | Suggest condition-monitoring methods based on equipment type and observed failure modes. | `MaintenanceStrategyProfileBuilderTool` -> `MaintenanceMixAnalyzerTool` -> `FailureModeCoverageAnalyzerTool` -> `FrequencyRiskAnalyzerTool` -> `MaintenanceStrategyGapDetectorTool` -> `ConditionMonitoringOpportunityAnalyzerTool` |
| Reliability Improvement Agent | `full_improvement_plan` | Run the full improvement workflow from opportunity estimation through roadmap sequencing. | `ValueEstimatorTool` -> `ActionPlanBuilderTool` -> `OutcomeReporterTool` -> `RoadmapPlannerTool` |
| Reliability Improvement Agent | `estimate_opportunities` | Rank improvement opportunities from corrective-like history, cost, downtime, repeats, and criticality. | `ValueEstimatorTool` |
| Reliability Improvement Agent | `build_action_plans` | Convert improvement opportunities into draft actions, owners, milestones, and deliverables. | `ValueEstimatorTool` -> `ActionPlanBuilderTool` |
| Reliability Improvement Agent | `define_outcomes` | Define baseline measures, expected outcomes, and reporting cadence for opportunities. | `ValueEstimatorTool` -> `ActionPlanBuilderTool` -> `OutcomeReporterTool` |
| Reliability Improvement Agent | `plan_roadmap` | Sequence opportunities into `now`, `next`, and `later` roadmap horizons. | `ValueEstimatorTool` -> `ActionPlanBuilderTool` -> `OutcomeReporterTool` -> `RoadmapPlannerTool` |

### Reliability Agent tools

- `ReliabilityAgentOrchestrator` — coordinates specialist tool calls through
  the configured model provider.
- `SpecialistRegistry` — exposes the available specialist capabilities and
  dispatches validated calls.
- `DuplicateCallGuard` — suppresses repeated specialist calls with the same
  arguments during one response loop.
- `ProgressStreamer` — streams live review, specialist, tool, and synthesis
  progress events.
- `ContextBuilder` — builds bounded chat context from the system prompt,
  memory, history, and the latest user request.
- `MemoryService` — updates and compacts conversation memory for follow-up
  questions.
- `AnswerQualityGate` — reviews the draft answer for evidence support,
  completeness, and honest limitations; allows up to three revision loops
  before returning the best supported answer with clear caveats.

### Master Data Agent tools

- `EquipmentSearchTool` — searches stored equipment by text and asset filters,
  returning paginated equipment records plus status and equipment-type counts.

### Defect Elimination Agent tools

- `ReliabilityMetricsTool` — summarizes work-order volume, activity mix, cost,
  downtime, date range, and corrective-to-preventive ratio.
- `DefectEliminationAgent` — selects focused internal paths for overview, bad
  actor, repeat failure, MTBF, Weibull, and RCA-preparation requests while
  keeping one specialist route exposed to the Reliability Agent.
- `BadActorAnalysisTool` — ranks high-impact equipment using corrective events,
  downtime, cost, MTTR, and MTBF context.
- `RepeatFailureDetectionTool` — finds recurring equipment and failure-mode
  patterns from linked work orders.
- `MTBFCalculationTool` — calculates asset-level mean time between corrective
  repair events.
- `WeibullAnalysisTool` — estimates failure behavior and life-distribution
  indicators where enough interval history exists.
- `RCAEvidencePlanningTool` — identifies evidence, interviews, records, and
  containment actions needed for RCA.
- `FiveWhysGeneratorTool` — drafts structured 5 Whys prompts for repeat
  failures.
- `RCATemplateBuilderTool` — creates RCA worksheet sections and starter
  questions.
- `DefectEliminationCharterGeneratorTool` — creates improvement charters with
  impact, hypotheses, evidence needs, actions, success criteria, and
  verification plans.

Recommendation synthesis for Defect Elimination is implemented inside
`DefectEliminationAgent` rather than as a separate tool class.

### Maintenance Strategy Agent tools

- `MaintenanceStrategyProfileBuilderTool` — summarizes existing maintenance
  strategy tasks, active task count, task types, and frequency details.
- `MaintenanceStrategyAgent` — selects focused internal paths for strategy
  profile summaries, maintenance mix, coverage, frequency, gap,
  monitoring-opportunity, and full strategy review requests while keeping one
  specialist route exposed to the Reliability Agent.
- `MaintenanceMixAnalyzerTool` — summarizes work-order mix, corrective to
  preventive ratio, cost, and downtime.
- `FailureModeCoverageAnalyzerTool` — compares observed failure modes with
  active strategy task descriptions to classify coverage.
- `FrequencyRiskAnalyzerTool` — compares task intervals with observed repeat
  failure recurrence to flag weak intervals for review.
- `MaintenanceStrategyGapDetectorTool` — identifies missing active strategies,
  uncovered failure modes, and partial coverage gaps.
- `ConditionMonitoringOpportunityAnalyzerTool` — suggests PdM or CBM methods
  based on equipment type and observed failure modes.
- `MaintenanceStrategyRecommendationBuilderTool` — returns bounded
  `keep`, `modify`, `add`, and `engineering_review` recommendations from the
  evidence produced by the preceding tools.

### Reliability Improvement Agent tools

- `ValueEstimatorTool` — ranks improvement opportunities from corrective-like
  work orders, downtime, cost, repeat failures, and criticality.
- `ReliabilityImprovementAgent` — selects focused internal paths for
  opportunity estimation, action plans, outcome measures, roadmap sequencing,
  and full improvement planning requests while keeping one specialist route
  exposed to the Reliability Agent.
- `ActionPlanBuilderTool` — creates draft owners, actions, milestones, and
  deliverables for each opportunity.
- `OutcomeReporterTool` — defines baseline measures, expected outcomes, and
  reporting cadence.
- `RoadmapPlannerTool` — sequences opportunities into `now`, `next`, and
  `later` roadmap horizons.

## Memory Architecture

Conversation memory is a durable Markdown summary stored on each conversation,
separate from the full message history. It preserves long-lived reliability
context such as objectives, equipment identifiers, known facts, assumptions,
decisions, recommended actions, and open questions.

On each chat turn, `ConversationChatService` loads the conversation, previous
messages, and current `memory_markdown`. `ContextBuilder` injects the memory as
a system message alongside the Reliability Agent system prompt, the latest
bounded conversation history, and the current user request. This keeps recent
dialogue available while giving durable facts a predictable place in the model
context.

Memory is token-budgeted separately from chat history. The current implementation
reserves up to one tenth of the provider context window for memory, one quarter
for the response, and a small safety margin. If the memory exceeds its budget,
`MemoryService` compacts it before the response is generated.

After the assistant response is saved, `MemoryService` updates the Markdown
memory from the previous memory, latest user message, and latest assistant
response. Updates use fixed headings to keep confirmed facts, assumptions,
decisions, recommended actions, and open questions distinct. Each saved memory
state is also recorded as a `ConversationMemoryRevision` with the message
sequence number it covers.

Memory is concise and durable rather than a full
transcript. Detailed history remains in persisted messages, while memory carries
forward the stable context needed for follow-up reliability analysis.

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
