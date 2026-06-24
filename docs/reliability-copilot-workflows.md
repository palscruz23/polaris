# Reliability Copilot Natural-Language Workflows

## Purpose

Reliability Copilot workflows let a user describe a reliability job in natural language and run it either once or on a schedule. A workflow such as "Check breakdown work orders in the past week and see if they have strategy gaps" should reuse the existing Reliability Agent orchestration pattern, specialist agents, deterministic tools, and progress reporting, then email a structured report to the requesting user.

## Example user experience

1. The user enters a natural-language workflow request in the Reliability Copilot:
   - "Check breakdown work orders in the past week and see if they have strategy gaps. Send me the report."
   - "Every Monday at 8am, review last week's emergency work orders for PM coverage gaps and email the maintenance planner."
2. The copilot clarifies missing details only when needed, such as recipients, schedule, asset scope, or report format.
3. The copilot performs a trial run and shows the answer, evidence, and tool trace for user review.
4. If the user is happy with the trial answer, the copilot shows a workflow preview containing:
   - Trigger: once-off or scheduled.
   - Scope: work-order type, lookback window, assets, sites, and criticality filters.
   - Analysis steps: data retrieval, breakdown filtering, strategy review, gap detection, recommendations, and report generation.
   - Delivery: email recipients and cadence.
5. The user confirms the workflow only after accepting the trial result.
6. The backend saves the reusable workflow recipe, executes future runs from that recipe, stores the run history, and emails a report with findings, evidence, and recommended actions.

## Goals

- Convert natural-language workflow instructions into a validated workflow plan.
- Support arbitrary reliability questions by capturing the specialist/tool sequence used during a successful trial answer, rather than hard-coding every workflow pattern up front.
- Reuse the existing Reliability Agent, specialist registry, Maintenance Strategy Agent, Defect Elimination Agent, Master Data Agent, and deterministic tool pattern.
- Support both once-off execution and scheduled recurring execution.
- Produce auditable workflow runs with tool inputs, tool outputs, report content, delivery status, and errors.
- Email reports to the user or configured recipients.
- Keep workflow execution bounded, observable, cancellable, and safe.

## Non-goals for the first release

- Fully autonomous changes to maintenance strategies, CMMS master data, or work orders.
- Multi-tenant billing, approvals, or enterprise policy engines beyond basic authorization.
- Complex branching visual workflow editing.
- External CMMS write-back; first release should be read-only plus report delivery.

## High-level architecture

```text
Web UI / API
   |
   v
Workflow Request Parser
   |
   v
Workflow Planner and Validator ---- Trial Run ---- User Confirmation
   |
   v
Workflow Definition Store ---- Scheduler
   |                              |
   v                              v
Workflow Runner <----------- Scheduled Trigger
   |
   +--> Reliability Agent Orchestrator
   |       +--> Master Data Agent
   |       +--> Defect Elimination Agent
   |       +--> Maintenance Strategy Agent
   |       +--> Reliability Improvement Agent (future)
   |
   +--> Report Builder
   |
   +--> Email Delivery Service
   |
   v
Workflow Run History, Logs, and Notifications
```

## Core components

### 1. Workflow request parser

The parser converts natural-language instructions into a typed workflow draft.

Responsibilities:

- Extract the workflow objective.
- Detect whether the request is once-off or scheduled.
- Extract schedule details, such as timezone, day, time, interval, and lookback window.
- Extract data scope, including work-order types, activity types, asset filters, functional locations, criticality, and date range.
- Extract report delivery preferences, including recipients, subject, format, and optional summary depth.
- Identify missing required fields and generate clarification questions.

Suggested draft schema:

```json
{
  "name": "Weekly breakdown strategy gap review",
  "objective": "Find breakdown work orders and identify maintenance strategy gaps",
  "trigger": {
    "type": "scheduled",
    "cron": "0 8 * * MON",
    "timezone": "Australia/Brisbane"
  },
  "scope": {
    "work_order_activity_types": ["corrective", "emergency"],
    "lookback": { "value": 7, "unit": "days" },
    "equipment_numbers": [],
    "functional_locations": [],
    "criticalities": []
  },
  "analysis": {
    "steps": [
      "retrieve_breakdown_work_orders",
      "group_by_equipment_and_failure_mode",
      "review_maintenance_strategy",
      "detect_strategy_gaps",
      "prioritize_recommendations"
    ]
  },
  "delivery": {
    "channels": ["email"],
    "recipients": ["requesting_user"],
    "format": "markdown_html"
  }
}
```


### 2. Trial run and answer acceptance

Before saving a reusable workflow, the system should run the user's request once as a trial and ask whether the user is happy with the answer. This avoids saving a workflow that technically executes but does not match the user's intent.

Responsibilities:

- Execute the natural-language request through the Reliability Agent using the same specialist registry and deterministic tools available to normal chat.
- Capture the final answer, evidence, tool calls, tool arguments, tool outputs, model-selected specialists, and report preview.
- Ask the user to accept, reject, or refine the trial result.
- If the user refines the request, re-run the trial and replace the candidate workflow recipe with the updated trace.
- Save the workflow only after explicit user acceptance.
- Store the accepted trial run as version `1` of the workflow recipe so scheduled runs reproduce the validated approach.

Acceptance options:

- `accept_and_save_once`: save the workflow as a once-off reusable job and optionally send the current report.
- `accept_and_schedule`: save the workflow with recurrence and delivery settings.
- `refine`: collect additional natural-language feedback and re-run the trial.
- `discard`: keep the chat answer but do not save a workflow.

### 3. Workflow tool trace meta-tool

A single hard-coded workflow such as breakdown strategy-gap review is useful for an MVP, but it does not cover the broad range of reliability questions users may ask. To support other questions, add a meta-tool that records how the agent answered a query and converts the successful trace into a reusable workflow recipe.

Proposed meta-tool: `WorkflowRecipeRecorder`.

Responsibilities:

- Observe each agent turn during a trial run.
- Save the ordered list of specialists, deterministic tools, normalized arguments, data filters, generated report sections, and delivery settings used to answer the user's question.
- Generalize relative date phrases such as "past week" into reusable runtime parameters such as `lookback: 7 days`.
- Mark which values are fixed and which values should be resolved at each run, for example exact timestamps are runtime values while selected equipment numbers may be fixed.
- Remove duplicate or exploratory tool calls that did not contribute to the accepted final answer.
- Validate that every recorded step is allowed for unattended execution.
- Version the recipe so future edits or accepted refinements do not overwrite historical runs.

Example recorded recipe shape:

```json
{
  "recipe_version": 1,
  "source_query": "Check breakdown work orders in the past week and see if they have strategy gaps",
  "runtime_parameters": {
    "window": { "type": "lookback", "value": 7, "unit": "days" },
    "timezone": "user_default"
  },
  "tool_trace": [
    {
      "agent": "defect_elimination",
      "tool": "WorkOrderQueryTool",
      "arguments": { "activity_types": ["corrective", "emergency"], "window": "runtime.window" }
    },
    {
      "agent": "maintenance_strategy",
      "tool": "StrategyGapDetector",
      "arguments": { "equipment_numbers": "previous_step.affected_equipment" }
    },
    {
      "agent": "reporting",
      "tool": "ReportBuilderTool",
      "arguments": { "sections": ["summary", "gaps", "recommendations", "evidence"] }
    },
    {
      "agent": "delivery",
      "tool": "EmailDeliveryTool",
      "arguments": { "recipients": ["requesting_user"] }
    }
  ],
  "acceptance": {
    "accepted_by_user": true,
    "accepted_trial_run_id": "workflow_run_id"
  }
}
```

This approach lets the workflow system start with the user's actual accepted answer path. Over time, common accepted traces can be promoted into first-class workflow templates, while uncommon questions can still be scheduled safely if their traces pass validation.

### 4. Workflow planner and validator

The planner turns a draft into an executable workflow definition.

Responsibilities:

- Map the user's intent and accepted trial trace to allowed workflow steps and specialist tools.
- Validate required fields, permissions, date windows, schedules, and recipient rules.
- Estimate cost and runtime where practical.
- Present the accepted trial answer and workflow preview before saving or scheduling.
- Enforce bounded execution, including maximum specialist calls, maximum assets, maximum work orders, and maximum report size.

Validation examples:

- A once-off job needs an executable date range and at least one delivery recipient.
- A scheduled job needs a valid timezone and recurrence.
- Work-order lookback windows should have a configurable maximum, for example 90 days for the first release.
- Email recipients should be restricted to the user's organization domain unless an administrator allows external delivery.

### 5. Workflow definition store

Persist confirmed workflows separately from individual runs.

Minimum fields:

- `id`
- `owner_user_id`
- `name`
- `status`: `draft`, `active`, `paused`, `archived`
- `trigger_type`: `once`, `scheduled`
- `schedule_expression`
- `timezone`
- `workflow_definition_json`
- `accepted_recipe_json`
- `accepted_trial_run_id`
- `version`
- `created_at`
- `updated_at`
- `last_run_at`
- `next_run_at`

### 6. Scheduler

The scheduler starts active scheduled workflows at the correct time.

Requirements:

- Support cron-like schedules and timezone-aware next-run calculation.
- Use durable scheduling so missed runs can be detected after restarts.
- Prevent duplicate runs with idempotency keys and row-level locking or a distributed lock.
- Allow pause, resume, delete, and manual "run now" operations.
- Record skipped, failed, and retrying states.

Implementation options:

- Initial deployment: a backend worker using APScheduler or Celery Beat.
- Production scale: a task queue such as Celery, RQ, Dramatiq, Temporal, or a cloud scheduler feeding a durable queue.

### 7. Workflow runner

The runner executes workflow definitions and records workflow run history.

Responsibilities:

- Resolve relative time windows at run time, for example "past week" becomes exact UTC start and end timestamps.
- Query the reliability data set for matching work orders.
- Call specialist agents and tools using the same bounded orchestration model as the Reliability Agent.
- Capture structured intermediate outputs and tool exchanges.
- Build a report from findings.
- Send email and record delivery status.
- Emit progress events for live UI visibility and logs.

Run states:

- `queued`
- `running`
- `succeeded`
- `partially_succeeded`
- `failed`
- `cancelled`
- `skipped`

### 8. Specialist agents and tools

The workflow should reuse the existing agent pattern instead of introducing a separate analysis stack.

Initial workflow-to-agent mapping:

| Workflow step | Agent/tool family | Purpose |
| --- | --- | --- |
| Resolve asset scope | Master Data Agent | Find matching equipment and validate filters. |
| Retrieve and summarize breakdown history | Defect Elimination Agent tools | Identify bad actors, repeat failures, MTBF, costs, downtime, and evidence. |
| Review strategies for affected assets | Maintenance Strategy Agent tools | Profile active tasks, analyze maintenance mix, assess coverage, assess frequency risk, and detect strategy gaps. |
| Prioritize actions | Defect Elimination and Maintenance Strategy recommendations | Convert findings into ranked next actions. |
| Build report | Report Builder | Format findings, evidence, limitations, and recommendations for email. |

New or extended tools likely needed:

- `WorkOrderQueryTool`: filters work orders by date range, activity type, status, equipment, functional location, and criticality.
- `BreakdownWorkOrderClassifier`: normalizes breakdown definitions across corrective, emergency, and unplanned work-order types.
- `StrategyGapWorkflowTool`: coordinates work-order retrieval plus maintenance strategy review for only the affected assets and failure modes.
- `ReportBuilderTool`: converts structured findings into Markdown, HTML, and optional CSV attachments.
- `EmailDeliveryTool`: sends report email and records provider message IDs.

### 9. Report builder

The report builder should produce a concise but evidence-backed report.

Recommended report sections:

1. Executive summary.
2. Workflow scope and run window.
3. Breakdown work-order summary.
4. Assets with potential strategy gaps.
5. Failure modes with weak, partial, or missing maintenance coverage.
6. Frequency risks and condition-monitoring opportunities.
7. Recommended actions with priority, rationale, and evidence work orders.
8. Data quality limitations.
9. Appendix with detailed work-order and strategy evidence.

Report formats:

- HTML email body for readability.
- Markdown stored with the run record for auditability.
- Optional CSV attachments for detailed tables.

### 10. Email delivery service

Requirements:

- Send reports to the requesting user by default.
- Support additional recipients when authorized.
- Include unsubscribe or schedule-management links for recurring reports.
- Store delivery status, provider message ID, sent timestamp, recipient list, and failure reason.
- Avoid exposing secrets in logs.
- Retry transient delivery failures with exponential backoff.

Recommended providers:

- Resend, SendGrid, AWS SES, or SMTP for the first implementation.
- Use provider abstractions so the service can be swapped without changing workflow logic.

## Data model requirements

Suggested new tables:

### `workflow_definitions`

Stores confirmed workflow configurations.

Important columns:

- `id`
- `owner_user_id`
- `name`
- `description`
- `status`
- `trigger_type`
- `schedule_expression`
- `timezone`
- `definition_json`
- `created_at`
- `updated_at`
- `last_run_at`
- `next_run_at`

### `workflow_runs`

Stores each execution attempt.

Important columns:

- `id`
- `workflow_definition_id`
- `triggered_by`: `user`, `scheduler`, `api`
- `status`
- `window_start_at`
- `window_end_at`
- `started_at`
- `finished_at`
- `summary_json`
- `tool_trace_json`
- `user_acceptance_status`
- `report_markdown`
- `report_html`
- `error_message`

### `workflow_run_steps`

Stores step-level progress and outputs.

Important columns:

- `id`
- `workflow_run_id`
- `step_name`
- `agent_name`
- `tool_name`
- `status`
- `input_json`
- `output_json`
- `started_at`
- `finished_at`
- `error_message`

### `workflow_recipes`

Stores versioned accepted tool traces that can be replayed for once-off or scheduled jobs.

Important columns:

- `id`
- `workflow_definition_id`
- `version`
- `source_query`
- `accepted_trial_run_id`
- `recipe_json`
- `created_at`
- `created_by_user_id`

### `workflow_email_deliveries`

Stores email delivery audit data.

Important columns:

- `id`
- `workflow_run_id`
- `recipient_email`
- `subject`
- `status`
- `provider`
- `provider_message_id`
- `sent_at`
- `error_message`

## API requirements

Suggested endpoints:

- `POST /workflows/draft`
  - Input: natural-language instruction.
  - Output: workflow draft, missing fields, and preview.
- `POST /workflows/trial`
  - Input: workflow draft.
  - Output: trial run answer, evidence, tool trace, report preview, and acceptance actions.
- `POST /workflows`
  - Input: confirmed workflow definition plus accepted trial run or accepted recipe.
  - Output: stored workflow definition.
- `GET /workflows`
  - Lists the user's workflows.
- `GET /workflows/{workflow_id}`
  - Shows workflow configuration and latest run state.
- `POST /workflows/{workflow_id}/run`
  - Runs a workflow immediately.
- `POST /workflows/{workflow_id}/pause`
  - Pauses scheduled execution.
- `POST /workflows/{workflow_id}/resume`
  - Resumes scheduled execution.
- `GET /workflows/{workflow_id}/runs`
  - Lists run history.
- `GET /workflow-runs/{run_id}`
  - Shows run details, report, and delivery status.
- `GET /workflow-runs/{run_id}/events`
  - Streams progress events where supported.

## UI requirements

- Add a workflow creation entry point in the Reliability Copilot.
- Allow users to type a natural-language workflow request.
- Display extracted workflow details in an editable preview.
- Require a successful trial run and explicit user acceptance before saving schedules or sending recurring emails.
- Show workflow status, next run time, last run status, and owner.
- Show run history with report previews and delivery status.
- Provide controls for run now, pause, resume, edit, and delete.
- Show progress while a once-off job is running.

## Security and governance requirements

- Enforce user authorization for workflow creation, execution, and report access.
- Restrict workflow data access to assets and sites the user can view.
- Restrict email recipients according to organization policy.
- Sanitize report HTML before sending and rendering.
- Store secrets only in backend secret management or environment variables.
- Log tool calls and run summaries without leaking API keys or sensitive recipient metadata.
- Add rate limits and per-user workflow quotas.
- Require confirmation for recurring scheduled emails.

## Observability requirements

- Emit structured logs for workflow draft creation, validation, execution, tool calls, report generation, and email delivery.
- Track metrics for run count, success rate, duration, step failures, email delivery failures, and schedule lag.
- Surface user-friendly failure messages in the UI.
- Keep enough run history to audit reports and troubleshoot data issues.

## Failure handling requirements

- If no matching work orders are found, send a report stating that no breakdown work orders matched the run window.
- If analysis succeeds but email fails, mark the run `partially_succeeded` and expose retry delivery.
- If the trial answer is rejected, do not save the workflow; collect refinement feedback and run a new trial.
- If one specialist fails, continue only when remaining findings are still useful and clearly mark limitations.
- Use idempotency keys so retries do not send duplicate emails unless explicitly requested.
- Provide manual re-run and resend controls.

## Suggested implementation phases

### Phase 1: Once-off workflow MVP

- Add workflow draft parsing for natural-language requests.
- Add trial-run execution with user acceptance before workflow save.
- Add `WorkflowRecipeRecorder` to save accepted tool traces for arbitrary reliability questions.
- Support breakdown work-order strategy-gap workflow as the first promoted template, while allowing validated accepted traces for other questions.
- Add work-order date/type filtering.
- Reuse Maintenance Strategy Agent and Defect Elimination Agent outputs.
- Generate Markdown and HTML reports.
- Send report emails to the requesting user.
- Store workflow run history.

### Phase 2: Scheduled workflows

- Add workflow definitions and scheduler.
- Add pause, resume, run now, and run history UI.
- Add durable locks, retries, and missed-run detection.
- Add schedule-management links in email reports.

### Phase 3: Broader workflow library

- Add bad-actor watchlists, weekly reliability dashboards, overdue RCA follow-ups, PM optimization reviews, and reliability improvement action tracking.
- Add CSV attachments and configurable report templates.
- Add administrator controls for quotas, domains, and retention.

## Acceptance criteria

- A user can create a once-off workflow from: "Check breakdown work orders in the past week and see if they have strategy gaps. Email me the report."
- The system extracts a seven-day lookback window, breakdown work-order types, strategy-gap analysis, and the requesting user as the default email recipient.
- The workflow uses existing specialist agents and deterministic tools where possible.
- The system performs a trial run and saves the workflow only after the user accepts the answer.
- The system stores the workflow run, accepted tool trace, report content, tool evidence, and email delivery status.
- The report identifies affected assets, failure modes, strategy gaps, evidence work orders, and prioritized recommendations.
- A user can create a scheduled version of the same workflow with a valid recurrence after accepting the trial result.
- A user can create other reliability-question workflows when the accepted trial trace passes validation for unattended replay.
- Scheduled jobs run once per due interval and do not duplicate reports on retry.

## Step-by-step implementation requirements

This section turns the architecture above into an implementation checklist. Each step should be completed with tests, migration coverage where applicable, and a small user-reviewable increment.

### Step 1: Define typed workflow contracts

Requirements:

- Create backend schema types for workflow drafts, trial runs, accepted recipes, workflow definitions, workflow runs, workflow run steps, and email deliveries.
- Model trigger types as `once` and `scheduled`.
- Model workflow status values as `draft`, `active`, `paused`, and `archived`.
- Model run status values as `queued`, `running`, `succeeded`, `partially_succeeded`, `failed`, `cancelled`, and `skipped`.
- Include a typed `runtime_parameters` object for relative dates, user timezone, equipment scope, work-order filters, and delivery settings.
- Include a typed `tool_trace` object that records agent name, tool name, normalized arguments, runtime parameter references, output references, and whether the step is replayable unattended.
- Reject workflow contracts that contain unknown tools, unsafe tools, missing required runtime parameters, or unsupported trigger types.

### Step 2: Add database migrations and persistence models

Requirements:

- Add database migrations for `workflow_definitions`, `workflow_runs`, `workflow_run_steps`, `workflow_recipes`, and `workflow_email_deliveries`.
- Store workflow definitions independently from workflow runs.
- Store accepted workflow recipes as immutable versions linked to a workflow definition.
- Store the accepted trial run ID on the recipe and workflow definition.
- Store exact resolved run windows on each run, not just relative lookback rules.
- Store tool inputs and outputs for auditability, with size limits and redaction for sensitive fields.
- Add indexes for owner, status, next run time, workflow definition ID, and run status.
- Ensure deleting or archiving a workflow does not remove historical run records unless a retention policy explicitly allows it.

### Step 3: Implement workflow draft parsing

Requirements:

- Add a draft endpoint that accepts a natural-language workflow request and returns a structured workflow draft.
- Extract objective, trigger type, schedule, timezone, lookback window, work-order filters, asset filters, report format, and recipients.
- Default ambiguous recipients to the requesting user.
- Mark missing required fields as clarification questions instead of guessing.
- Normalize phrases such as "past week", "last 7 days", and "weekly Monday morning" into structured fields.
- Keep the original source query with the draft for auditability and recipe creation.
- Do not save a workflow definition from this step.

### Step 4: Implement the trial-run endpoint

Requirements:

- Add `POST /workflows/trial` to execute a draft once without saving it as an active workflow.
- Resolve runtime parameters, including exact `window_start_at` and `window_end_at`, before execution.
- Execute the request through the existing Reliability Agent orchestration and specialist registry.
- Capture final answer text, structured evidence, report preview, progress events, tool calls, tool arguments, and tool outputs.
- Save the trial as a `workflow_run` with `user_acceptance_status` set to `pending`.
- Return acceptance actions to the UI: accept once, accept and schedule, refine, or discard.
- Make trial runs idempotent for the same draft and user request ID where practical.

### Step 5: Implement `WorkflowRecipeRecorder`

Requirements:

- Record the ordered specialist and tool trace used during the trial run.
- Normalize exact timestamps back into runtime parameters when they came from relative user language.
- Preserve fixed user choices such as specific equipment numbers or functional locations.
- Remove duplicate, failed, or exploratory tool calls unless they are required evidence for the accepted answer.
- Mark each recorded step as replayable or not replayable.
- Reject recipes that include non-replayable steps for scheduled workflows.
- Version every accepted recipe starting at version `1`.
- Store the recipe only after the user accepts the trial answer.

### Step 6: Add user acceptance and refinement flow

Requirements:

- The UI must show the trial answer, report preview, evidence, and summarized tool trace before saving.
- The user must explicitly accept the trial result before the system creates a workflow definition or schedule.
- If the user selects `refine`, collect natural-language feedback, create a revised draft, and run a new trial.
- If the user selects `discard`, do not save a workflow definition or recipe.
- If the user accepts, update the accepted trial run with `user_acceptance_status = accepted`.
- Store rejected trial runs with `user_acceptance_status = rejected` so product teams can inspect common failure modes.

### Step 7: Create workflow definitions from accepted recipes

Requirements:

- Create workflow definitions only from accepted trial runs and accepted recipes.
- For once-off workflows, allow immediate report sending and keep the saved recipe available for manual reruns.
- For scheduled workflows, require recurrence, timezone, owner, and delivery settings.
- Validate schedule expressions and calculate `next_run_at` before activating a workflow.
- Save workflow definitions as `active` only after validation succeeds.
- Support `paused` status at creation if the user wants to save but not run the workflow yet.

### Step 8: Implement the workflow runner

Requirements:

- Load the active recipe version for a workflow definition.
- Resolve all runtime parameters at run time, including relative date windows and user timezone.
- Execute replayable steps in recorded order unless a promoted template provides a safer deterministic implementation.
- Persist each step in `workflow_run_steps` with inputs, outputs, timestamps, status, and error message.
- Preserve the existing maximum specialist-call and output-size limits.
- Build a final run summary even when no matching records are found.
- Mark the run `succeeded`, `partially_succeeded`, `failed`, `cancelled`, or `skipped` according to step and delivery outcomes.

### Step 9: Implement report generation

Requirements:

- Build a Markdown report for every run and store it on the run record.
- Build sanitized HTML for email delivery and UI rendering.
- Include objective, run window, filters, summary, findings, evidence, recommendations, limitations, and next actions.
- Include a clear no-results report when no work orders or assets match the scope.
- Include enough evidence for the user to understand why the answer was generated, including relevant work orders and strategies.
- Keep reports below configurable size limits and move detailed tables to attachments or appendices where needed.

### Step 10: Implement email delivery

Requirements:

- Send emails only after the user accepts a trial for once-off delivery or after a scheduled workflow produces a report.
- Default recipients to the requesting user and enforce recipient authorization rules.
- Store one `workflow_email_deliveries` record per recipient.
- Store provider, provider message ID, delivery status, sent timestamp, subject, and failure reason.
- Retry transient failures with exponential backoff.
- Do not send duplicate emails on run retries unless the user explicitly requests resend.
- Include workflow management links for scheduled reports.

### Step 11: Implement scheduler support

Requirements:

- Add a scheduler or worker that finds active workflows due at or before the current time.
- Use locking or idempotency keys to prevent duplicate scheduled runs.
- Calculate the next run time in the workflow timezone.
- Detect missed runs after worker restarts and either run them or mark them skipped according to product policy.
- Support pause, resume, run now, edit, archive, and delete controls.
- Record scheduler-triggered runs with `triggered_by = scheduler`.

### Step 12: Add API and UI management surfaces

Requirements:

- Implement endpoints to list workflows, inspect workflow details, run now, pause, resume, archive, list runs, inspect runs, and stream run events.
- Show workflow status, trigger, next run time, last run status, owner, recipients, and active recipe version.
- Show run-level report, evidence, delivery status, and step-level trace.
- Allow the user to edit schedule and delivery settings without changing the accepted recipe.
- Require a new trial and acceptance when the user changes the core analysis question, scope, or tool recipe.

### Step 13: Add security, governance, and limits

Requirements:

- Check user authorization before drafting, trialing, saving, running, viewing, or emailing workflows.
- Enforce asset/site visibility on every trial and scheduled run.
- Redact secrets and sensitive recipient metadata from logs and tool traces.
- Limit maximum workflows per user, maximum scheduled frequency, maximum lookback window, maximum recipients, maximum tool calls, and maximum report size.
- Validate that accepted recipes contain only approved tools for unattended execution.
- Sanitize report HTML before email delivery or UI display.

### Step 14: Add observability and operational controls

Requirements:

- Emit structured logs for draft parsing, trial runs, recipe recording, workflow creation, scheduled execution, report generation, and email delivery.
- Track metrics for run duration, success rate, failure reason, schedule lag, email delivery failure, and recipe validation failure.
- Add user-facing error messages that explain whether the failure happened during parsing, analysis, report generation, scheduling, or email delivery.
- Add administrator-visible diagnostics for stuck, failed, or repeatedly skipped workflows.

### Step 15: Add automated tests

Requirements:

- Test draft parsing for once-off and scheduled natural-language examples.
- Test trial run creation and pending acceptance status.
- Test accepting a trial creates a workflow definition and versioned recipe.
- Test rejected and discarded trials do not create workflow definitions.
- Test recipe recording generalizes relative date windows into runtime parameters.
- Test scheduled runs resolve new windows at execution time.
- Test email failures produce `partially_succeeded` runs and retryable delivery records.
- Test authorization failures for unauthorized assets, workflows, runs, and email recipients.
- Test no-results workflows still produce a report.
- Test idempotency prevents duplicate scheduled runs and duplicate emails.

### Step 16: Release and rollout requirements

Requirements:

- Gate the feature behind a backend and frontend feature flag for the first release.
- Start with the breakdown work-order strategy-gap workflow as a promoted template.
- Allow arbitrary accepted tool-trace workflows only when recipe validation passes.
- Roll out once-off workflows before scheduled workflows.
- Monitor trial acceptance rate, scheduled run success rate, and email delivery success before broadening access.
- Provide a rollback plan that disables scheduling without deleting saved workflow definitions or historical runs.
