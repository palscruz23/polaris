# Polaris Watch Design

## Problem

Polaris can review work orders and maintenance strategies on demand, but it
does not yet push routine reliability findings to the maintenance team. The
first scheduled workflow feature, Polaris Watch, should review fresh work-order
data daily and send focused findings to Microsoft Teams without requiring a
full workflow builder or in-app scheduler.

## Goals

- Import updated work-order and work-order failure-mode data into Postgres on a
  daily schedule.
- Run three predefined Polaris Watch templates independently each day.
- Send one Microsoft Teams message per review template.
- Persist enough import, review, report, and delivery state for auditability and
  future UI scheduler work.
- Keep Webex as a future notification provider without implementing it in v1.

## Non-Goals

- User-created schedules in the Polaris UI.
- Natural-language workflow creation, trial-run acceptance, or reusable recipe
  recording.
- Automatic changes to work orders, failure modes, maintenance strategies, or
  CMMS records.
- Webex delivery in v1.

## Chosen Approach

Polaris Watch uses four separate GitHub Actions cron workflows:

1. Daily reliability data import.
2. Daily breakdown strategy gap review.
3. Daily bad actor watchlist review.
4. Daily maintenance strategy health check review.

Each workflow invokes a backend CLI command. GitHub Actions owns scheduling and
logs. Polaris owns data import, reliability analysis, report generation,
Teams delivery, and run persistence.

This approach matches the existing backend CLI pattern used by nightly
evaluations while avoiding the infrastructure cost of an in-app scheduler for
the first release.

## Predefined Polaris Watch Templates

### Breakdown Strategy Gap Review

Template ID: `breakdown_strategy_gap`

Purpose: review recent corrective and emergency work orders, identify affected
assets and failure modes, and check whether active maintenance strategies cover
the observed issues.

Default window: 1 day.

Expected outputs:

- Corrective and emergency work-order summary.
- Affected assets and failure modes.
- Uncovered or partially covered repeated failure modes.
- Strategy gaps, frequency risks, and recommended engineering actions.
- Evidence work orders and data limitations.

### Bad Actor Watchlist

Template ID: `bad_actor_watchlist`

Purpose: identify equipment driving reliability impact by repeat failures,
downtime, cost, and corrective work volume.

Default window: 30 days.

Expected outputs:

- Ranked bad actor assets.
- Repeat failure groups.
- Failure-mode bad actors where available.
- Recommended investigation priorities.
- Evidence work orders and data limitations.

### Maintenance Strategy Health Check

Template ID: `maintenance_strategy_health_check`

Purpose: review high-risk or recently affected assets for maintenance strategy
coverage gaps, weak intervals, and recurring partial-coverage patterns.

Default window: 30 days.

Expected outputs:

- Strategy profile summary for selected assets.
- Maintenance mix context.
- Coverage gaps and frequency risks.
- Keep, modify, add, or engineering-review recommendations.
- Evidence work orders and data limitations.

## Runtime Architecture

```text
GitHub Actions cron
  -> backend CLI command
  -> Postgres
  -> existing reliability agents and deterministic tools
  -> scheduled review report builder
  -> Teams notification provider
  -> scheduled review run history
```

The data import workflow should run before the review workflows. The review
workflows should be offset by enough time for import completion.

Example schedule:

```text
00:05 - import daily reliability data
00:20 - breakdown strategy gap review
00:30 - bad actor watchlist
00:40 - maintenance strategy health check
```

## CLI Commands

### Daily Data Import

```bash
python -m app.cli.import_daily_reliability_data \
  --work-orders-csv data/work_orders.csv \
  --work-order-failure-modes-csv data/work_order_failure_modes.csv
```

Responsibilities:

- Read clean daily work-order CSV input.
- Read clean daily work-order failure-mode link CSV input.
- Upsert work orders by `order_number`.
- Upsert work-order failure-mode links by work order and failure mode.
- Record import batch metadata.
- Fail clearly for unknown equipment or unknown failure modes in v1.
- Avoid Teams messages on success.
- Optionally send a Teams failure alert when import fails.

### Scheduled Review

```bash
python -m app.cli.run_scheduled_review \
  --template breakdown_strategy_gap \
  --lookback-days 1
```

```bash
python -m app.cli.run_scheduled_review \
  --template bad_actor_watchlist \
  --lookback-days 30
```

```bash
python -m app.cli.run_scheduled_review \
  --template maintenance_strategy_health_check \
  --lookback-days 30
```

Responsibilities:

- Validate that the template ID is one of the supported predefined templates.
- Resolve the exact UTC run window from lookback days and timezone.
- Execute the selected template through existing specialist agents and tools.
- Build a concise Teams-ready Markdown report.
- Send the report to Microsoft Teams.
- Persist run status, report content, and delivery metadata.

## Components

### DailyReliabilityDataImportService

Imports daily work-order and work-order failure-mode data. This should reuse
the existing reliability seed loader concepts but be scoped to incremental
daily upserts instead of full sample-data loads.

Key boundary: the import service owns source-row validation and persistence. It
does not perform reliability analysis.

### ScheduledReviewService

Coordinates one predefined review template. It selects the correct analysis
path, calls existing agents, and returns structured findings for report
generation.

Key boundary: the service owns orchestration for unattended reviews. Specialist
agents continue to own reliability-specific analysis.

### ScheduledReviewReportBuilder

Converts structured findings into concise Markdown suitable for Teams.

Report sections:

- Title and run window.
- Executive summary.
- Key findings.
- Recommended actions.
- Evidence.
- Data limitations.

### NotificationDeliveryService

Provider interface for outbound notifications.

V1 provider:

- `TeamsNotificationProvider`

Future provider:

- `WebexNotificationProvider`

The review engine should depend on the interface, not the Teams implementation.

### TeamsNotificationProvider

Posts a Markdown-oriented message to a configured Teams workflow webhook URL.
The provider should keep secrets out of logs and persist delivery status,
provider response details, and failure messages.

## Data Model

### scheduled_review_runs

Stores each review execution.

Important fields:

- `id`
- `template_id`
- `status`: `running`, `succeeded`, `partially_succeeded`, `failed`
- `window_start_at`
- `window_end_at`
- `started_at`
- `finished_at`
- `report_markdown`
- `summary_json`
- `error_message`
- `created_at`

### scheduled_review_deliveries

Stores notification delivery attempts.

Important fields:

- `id`
- `scheduled_review_run_id`
- `provider`: `teams`
- `destination_label`
- `status`: `pending`, `sent`, `failed`
- `sent_at`
- `provider_response_json`
- `error_message`
- `created_at`

Import history can continue using `import_batches` for v1. If daily import
needs more detail later, add a dedicated import-run table instead of overloading
review-run records.

## Configuration

Required GitHub repository secrets:

```text
DATABASE_URL
OPENROUTER_API_KEY
SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL
```

Optional environment variables:

```text
SCHEDULED_REVIEW_DEFAULT_TIMEZONE=Australia/Sydney
SCHEDULED_REVIEW_TEAMS_DESTINATION_LABEL=Reliability Team
```

The GitHub Actions workflow can provide CSV paths directly as command
arguments. V1 assumes each workflow run already has the CSV files available,
either committed to the repository, generated by an earlier workflow step, or
downloaded from an approved source before the backend CLI command is invoked.

## Error Handling

- If import fails, fail the import workflow and do not send success noise to
  Teams.
- If a review finds no matching work orders, send a successful report stating
  that no records matched the window.
- If analysis succeeds but Teams delivery fails, mark the run
  `partially_succeeded`.
- If one review fails, the other review workflows remain independent and can
  still run.
- Secrets must not be written to CLI output, structured logs, or persisted
  error fields.

## Testing

Backend tests should cover:

- Incremental work-order upserts by `order_number`.
- Incremental work-order failure-mode link upserts.
- Import failure on unknown equipment or unknown failure modes.
- Template ID validation.
- Window resolution.
- Each template calling the expected existing agent path.
- Report builder output for empty and non-empty findings.
- Teams provider success and failure behavior with HTTP mocked.
- CLI argument parsing for import and review commands.

## Future UX-Friendly Scheduler Path

The v1 shape intentionally separates template execution from schedule
ownership. A future UI scheduler can reuse the same `ScheduledReviewService`,
report builder, notification interface, and run-history tables while replacing
GitHub Actions cron with database-backed schedule definitions.

Future UI additions:

- Admin page listing predefined review schedules.
- Enable, pause, resume, and run-now controls.
- Editable Teams destination per schedule.
- Run history and report preview.
- Webex destination support through the same notification interface.
