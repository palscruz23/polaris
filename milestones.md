# Open Reliability Development Milestones

This roadmap tracks the high-level milestones needed to develop Open Reliability Copilot from the current chat foundation into the PRD vision: an AI-powered reliability engineering platform combining work order intelligence, maintenance strategy intelligence, and reliability knowledge intelligence.

## Status Legend

- `Done` - Implemented in the current project.
- `In Progress` - Partially implemented or represented in the product skeleton.
- `Next` - Recommended next implementation focus.
- `Planned` - Not started yet.

## Milestones

| Milestone | Status | Outcome |
| --- | --- | --- |
| Project foundation | Done | Monorepo structure with Next.js frontend, FastAPI backend, Postgres-oriented persistence, migrations, and local development setup. |
| Reliability Agent chat | Done | User-facing chat experience for reliability engineering questions. |
| Conversation persistence | Done | Conversations and messages are stored in PostgreSQL with conversation history and session recovery. |
| Conversation memory | Done | Per-session Markdown memory captures durable context for follow-up questions. |
| Provider abstraction | Done | Backend uses a model-provider interface so chat logic is not tightly coupled to one LLM provider. |
| Product-state cleanup | Done | Homepage, README, PRD, and workflow naming now reflect current backend capability and use one agent naming scheme. |
| Master Data Agent v1 | Next | Upload work order CSV/XLSX files, preview rows, detect dataset type, suggest column mappings, validate required fields, and produce a data readiness report. |
| Reliability data model | Planned | Define normalized records for equipment, work orders, maintenance strategies, failure modes, import batches, and validation results. |
| Data Mapping Wizard UI | Planned | Guided frontend workflow for upload, preview, mapping confirmation, validation, and import readiness scoring. |
| Agent tool orchestration | Planned | Allow the Reliability Agent to select and execute backend analysis tools instead of only responding from prompt context. |
| Defect Elimination Agent v1 | Planned | Analyze imported work orders for bad actors, repeat failures, corrective/preventive split, MTBF, and MTTR. Generate structured defect elimination charters, problem statements, hypotheses, evidence needs, and RCA plans from work order history. |
| Strategy Agent v1 | Planned | Review PM tasks, identify strategy gaps, assess failure mode coverage, and recommend task/frequency changes. |
| Reliability Improvement Agent v1 | Planned | Convert technical findings into ranked opportunities, value estimates, action plans, and executive summaries. |
| Reliability Knowledge Base v1 | Planned | Ingest RCA reports, FMEAs, OEM manuals, site standards, and other documents for retrieval-augmented reliability guidance. |
| pgvector search | Planned | Store document and record embeddings in Postgres with pgvector for similar work orders, previous RCAs, known failure modes, and engineering knowledge retrieval. |
| Integrated agent-team workflow | Planned | Reliability Agent coordinates Master Data, Defect Elimination, Strategy, and Reliability Improvement agents into a consolidated final recommendation. |
| Reporting and roadmap outputs | Planned | Generate monthly reliability reports, opportunity pipelines, prioritized action plans, and reliability roadmaps. |
| Production readiness | Planned | Add authentication, authorization, file storage hardening, observability, background jobs, deployment configuration, and robust error handling. |

