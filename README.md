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

- **Specialist router** — selects the best specialist agent for each user
  request based on the reliability question and available context.
- **Bounded multi-call loop** — calls specialist agents sequentially, with a
  limit of five specialist calls per request before the Reliability Agent
  synthesises a final answer.
- **Duplicate-call suppression** — prevents redundant specialist invocations
  when the same specialist has already addressed the request.
- **Live progress streaming** — sends natural-language coordination updates to
  the frontend while specialist analysis is running.
- **Conversation memory update** — preserves key reliability context from the
  exchange so follow-up questions can reuse asset, work-order, and strategy
  details.

### Master Data Agent tools

- **Equipment search** — finds equipment by keyword, asset tag, functional
  location, facility/system context, and other asset filters.
- **Paginated match summaries** — returns equipment matches in pages with
  total match counts so large result sets remain reviewable.

### Defect Elimination Agent tools

- **Reliability metrics summary** — calculates asset-level and system-level
  reliability totals from work order history, including failure counts,
  downtime, and maintenance cost.
- **Bad actor analysis** — ranks equipment by failure count, downtime hours,
  and maintenance cost to highlight priority assets.
- **Repeat failure detection** — identifies recurring equipment/failure-mode
  combinations across work order time windows.
- **MTBF calculation** — estimates mean time between failures from repair work
  order history for comparable assets.
- **RCA evidence planning** — lists the evidence, stakeholders, and data needed
  to validate repeat-failure root causes.
- **5 Whys generation** — drafts structured 5 Whys prompts and likely themes
  for failure mode investigation.
- **RCA template construction** — creates an RCA worksheet with problem
  statement, evidence needs, hypotheses, and recommended next questions.
- **Defect elimination charter generation** — builds a charter with business
  case, scope, hypotheses, actions, success measures, and owners for priority
  repeat failures.
- **Prioritised recommendations** — produces evidence-backed next actions from
  the metrics, repeat failures, RCA outputs, and charters.

### Maintenance Strategy Agent tools

- **Maintenance task profile review** — summarises planned tasks for an asset
  or equipment context.
- **Maintenance mix breakdown** — groups strategy tasks by PM, PdM, CBM,
  corrective, and run-to-failure work types.
- **Failure-mode coverage analysis** — compares strategy tasks against known
  failure modes to show covered and uncovered risks.
- **Frequency risk assessment** — reviews scheduled task frequencies for
  under-maintenance and over-maintenance risk.
- **Strategy gap identification** — highlights missing controls, duplicated
  tasks, unsupported intervals, and weak links between failure modes and tasks.
- **Condition-monitoring opportunity review** — identifies candidates for PdM or
  CBM based on failure modes, equipment context, and current task mix.
- **Evidence-backed strategy recommendations** — proposes maintenance strategy
  changes with supporting rationale from available asset and task data.

### Reliability Improvement Agent tools

- **Planned value workflow** — planned toolset for quantifying expected value
  from reliability improvement opportunities.
- **Action-plan workflow** — planned toolset for converting approved
  opportunities into owners, milestones, and deliverables.
- **Reporting workflow** — planned toolset for tracking benefits, progress,
  and reliability outcomes.
- **Roadmap workflow** — planned toolset for sequencing initiatives into a
  reliability improvement roadmap.

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
