<p align="center">
  <img src="apps/web/public/brand/polaris-logo.png" alt="Polaris logo" width="48" height="48" />
  <img src="apps/web/public/brand/polaris-comp1.png" alt="Polaris" width="340" />
</p>

Open Reliability's workspace powered by Polaris, an AI Reliability Agent that guides engineers through data-driven analysis, maintenance strategy optimisation, and reliability decision-making.

Polaris Agent can select and execute registered specialist capabilities through a bounded sequential multi-call loop. Master Data, Defect Elimination, and Maintenance Strategy are the active registered specialists; Reliability Improvement remains future-development code.

<p align="center">
  <a href="https://ask-polaris.vercel.app/">Link to Polaris Portal</a>
</p>

## Sample Demo

![Polaris Demo](polaris-demo.gif)

## Reliability Agent Workflow and Tooling

Polaris Reliability Agent coordinates specialists through deterministic tools and
orchestration components. Available tools and components by agent:

### Specialist routes and intents

Polaris Reliability Agent exposes one route per specialist agent. For specialist
routes with an `intent` argument, the Reliability Agent should choose the
narrowest intent that satisfies the user request; the specialist then manages
the internal deterministic tools required for that intent.

| Specialist | Intent | Description | Tool Calls (in sequence) |
| --- | --- | --- | --- |
| Master Data Agent | <small>n/a</small> | Search or list stored equipment so the user can find asset identifiers before deeper analysis. | `EquipmentSearchTool` |
| Defect Elimination Agent | <small><code>overview</code></small> | Run the full defect-elimination overview across reliability summary, equipment bad actors, repeat failures, failure-mode bad actors, and recommendations. | `ReliabilityMetricsTool`<br>`BadActorAnalysisTool`<br>`RepeatFailureDetectionTool`<br>`FailureModeBadActorAnalysisTool` |
| Defect Elimination Agent | <small><code>rank_bad_actors</code></small> | Rank high-impact equipment using corrective-like work history, downtime, cost, MTTR, and MTBF context. | `ReliabilityMetricsTool`<br>`BadActorAnalysisTool` |
| Defect Elimination Agent | <small><code>find_repeat_failures</code></small> | Find repeated equipment/failure-mode patterns that meet the occurrence threshold. | `ReliabilityMetricsTool`<br>`RepeatFailureDetectionTool` |
| Defect Elimination Agent | <small><code>rank_failure_mode_bad_actors</code></small> | Rank repeated equipment/failure-mode patterns from repeat-failure findings by recurrence, downtime, and cost. | `ReliabilityMetricsTool`<br>`RepeatFailureDetectionTool`<br>`FailureModeBadActorAnalysisTool` |
| Maintenance Strategy Agent | <small><code>full_strategy_review</code></small> | Run the full maintenance strategy review from profile through recommendations. | `MaintenanceStrategyProfileBuilderTool`<br>`MaintenanceMixAnalyzerTool`<br>`FailureModeCoverageAnalyzerTool`<br>`FrequencyRiskAnalyzerTool`<br>`MaintenanceStrategyGapDetectorTool`<br>`MaintenanceStrategyRecommendationBuilderTool` |
| Maintenance Strategy Agent | <small><code>summarize_strategy_profile</code></small> | Summarize existing maintenance strategy tasks, active task counts, types, frequencies, and statuses. | `MaintenanceStrategyProfileBuilderTool` |
| Maintenance Strategy Agent | <small><code>maintenance_mix</code></small> | Summarize preventive, inspection, condition-monitoring, corrective, and emergency work-order mix. | `MaintenanceStrategyProfileBuilderTool`<br>`MaintenanceMixAnalyzerTool` |
| Maintenance Strategy Agent | <small><code>check_coverage</code></small> | Compare observed failure modes with active strategy task descriptions to classify coverage. | `MaintenanceStrategyProfileBuilderTool`<br>`MaintenanceMixAnalyzerTool`<br>`FailureModeCoverageAnalyzerTool` |
| Maintenance Strategy Agent | <small><code>assess_frequency</code></small> | Compare task intervals with observed repeat-failure recurrence to flag engineering-review risks. | `MaintenanceStrategyProfileBuilderTool`<br>`MaintenanceMixAnalyzerTool`<br>`FailureModeCoverageAnalyzerTool`<br>`FrequencyRiskAnalyzerTool` |
| Maintenance Strategy Agent | <small><code>detect_gaps</code></small> | Identify missing active strategies, uncovered failure modes, and recurring partial-coverage gaps. | `MaintenanceStrategyProfileBuilderTool`<br>`MaintenanceMixAnalyzerTool`<br>`FailureModeCoverageAnalyzerTool`<br>`FrequencyRiskAnalyzerTool`<br>`MaintenanceStrategyGapDetectorTool` |

### Reliability Agent orchestration components

- `ReliabilityAgentOrchestrator` runs the bounded Reliability Agent loop:
  selects specialist routes, executes validated calls, suppresses duplicate
  calls with the same arguments, consolidates evidence, and returns the final
  response.
  - Final synthesis consolidates specialist evidence, applies synthesis
    guidance, optionally uses roadmap sequencing, and writes the user-facing
    answer.
  - Answer quality loop reviews and revises the draft answer through persisted
    model call phases: `agent_tool_selection`, `agent_final_synthesis`,
    `answer_review`, `answer_revision`, and `answer_revision_final`.
  - Roadmap sequencing helper uses `ROADMAP_PLANNER_TOOL_DEFINITION` as an
    optional final-synthesis tool definition, not a registered specialist
    capability. It is used only after specialist evidence has identified
    recommendations or opportunities that need `now`, `next`, and `later`
    sequencing.
  - Recommendation decision guidance uses `RECOMMENDATION_DECISION_MATRIX` as
    synthesis guidance, not a tool. It helps decide whether recommendations from
    Defect Elimination and Maintenance Strategy should become a formal
    investigation or a maintenance strategy improvement.
- `SpecialistRegistry` exposes the active top-level callable specialist
  capabilities to the Reliability Agent: `search_equipment_master`,
  `analyze_defect_elimination`, and `review_maintenance_strategy`. Each
  specialist then runs its own internal deterministic tools for the selected
  intent.
- `ToolCallCollector` records specialist sub-tool progress and streams review,
  specialist, deterministic-tool, synthesis, and answer quality stages to the
  chat UI.
- `ContextBuilder` builds bounded chat context from the Reliability Agent
  system prompt, durable memory, recent history, and the latest user request.
- `MemoryService` updates and compacts conversation memory for follow-up
  questions.

### Master Data Agent tools

- `EquipmentSearchTool` — searches stored equipment by text and asset filters,
  returning paginated equipment records plus status and equipment-type counts.

### Defect Elimination Agent tools

- `ReliabilityMetricsTool` — summarizes work-order volume, activity mix, cost,
  downtime, date range, and corrective-to-preventive ratio.
- `BadActorAnalysisTool` — ranks high-impact equipment using corrective events,
  downtime, cost, MTTR, and MTBF context.
- `RepeatFailureDetectionTool` — finds recurring equipment and failure-mode
  patterns from linked work orders.
- `FailureModeBadActorAnalysisTool` — ranks repeated equipment/failure-mode
  patterns from `RepeatFailureDetectionTool` output by recurrence, downtime,
  and cost.

Recommendation synthesis for Defect Elimination is implemented inside
`DefectEliminationAgent` rather than as a separate tool class.

### Maintenance Strategy Agent tools

- `MaintenanceStrategyProfileBuilderTool` — summarizes existing maintenance
  strategy tasks, active task count, task types, and frequency details.
- `MaintenanceMixAnalyzerTool` — summarizes executed work-order history by
  preventive, inspection, condition-monitoring, corrective, and emergency work;
  calculates the reactive-to-planned maintenance ratio; and totals cost and
  downtime so strategy reviews can compare the planned strategy against actual
  maintenance demand.
- `FailureModeCoverageAnalyzerTool` — compares observed failure modes with
  active strategy task descriptions to classify coverage.
- `FrequencyRiskAnalyzerTool` — compares task intervals with observed repeat
  failure recurrence to flag weak intervals for review.
- `MaintenanceStrategyGapDetectorTool` — identifies missing active strategies,
  uncovered failure modes, and partial coverage gaps.
- `MaintenanceStrategyRecommendationBuilderTool` — returns bounded
  `keep`, `modify`, `add`, and `engineering_review` recommendations from the
  evidence produced by the preceding tools, including condition-monitoring
  suggestions when observed failure modes have a suitable monitoring method.

### Future Reliability Improvement Agent tools

The Reliability Improvement Agent is intentionally disabled from the active
Reliability Agent specialist registry for now. Its implementation remains in
the codebase for future development, including `ValueEstimatorTool`,
`ActionPlanBuilderTool`, `OutcomeReporterTool`, and `RoadmapPlannerTool`.
`RoadmapPlannerTool` may still be used as a narrow Reliability Agent final
synthesis helper when already-identified opportunities need `now`, `next`, and
`later` sequencing.

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

- `apps/web` — Next.js frontend for Polaris.
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
OPENROUTER_APP_NAME=Polaris
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

Open Polaris at:

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

Polaris is licensed under the
[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for attribution information.
