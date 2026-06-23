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
| Homepage capability messaging | Done | Hero messaging now emphasizes high-level reliability benefits, and the secondary CTA links to the renamed capability roadmap section. |
| Homepage desktop fit pass | Done | Hero and planned architecture sections now use desktop-specific density rules so the main product story fits more comfortably in a desktop viewport. |
| Homepage mobile responsive pass | Done | Hero content, CTAs, benefit panel, and planned architecture diagram now adapt into a narrow-screen vertical layout. |
| Master Data Agent v1 | Planned | Parked for MVP because initial workflows will use clean data. Later: upload work order CSV/XLSX files, preview rows, detect dataset type, capture or suggest semantic column descriptions, require user review, suggest mappings, validate required fields, and produce a data readiness report. |
| Reliability data model | Done | Normalized backend records now cover equipment, work orders, maintenance strategies, failure modes, import batches, and validation results. |
| Clean data seed loader | Done | Backend CLI loads clean MVP CSV data into the reliability model with import batches, asset links, strategy records, work orders, and failure-mode links. |
| Data Mapping Wizard UI | Planned | Guided frontend workflow for upload, preview, mapping confirmation, validation, and import readiness scoring. |
| Agent tool orchestration | Planned | Allow the Reliability Agent to select and execute backend analysis tools instead of only responding from prompt context. |
| Defect Elimination Agent v1 | In Progress | Backend specialist agent and deterministic tools now produce MTBF-based bad actor rankings, repeat failure groups, reliability summary metrics, MTBF metrics, Weibull analysis, RCA evidence plans, 5 Whys prompts for repeat or specific failures, RCA templates for repeat or specific failures, defect elimination charters, and recommended next actions. Remaining scope: Reliability Agent orchestration. |
| Strategy Agent v1 | Planned | Review PM tasks, identify strategy gaps, assess failure mode coverage, and recommend task/frequency changes. |
| Reliability Improvement Agent v1 | Planned | Convert technical findings into ranked opportunities, value estimates, action plans, and executive summaries. |
| Reliability Knowledge Base v1 | Planned | Ingest RCA reports, FMEAs, OEM manuals, site standards, and other documents for retrieval-augmented reliability guidance. |
| pgvector search | Planned | Store document and record embeddings in Postgres with pgvector for similar work orders, previous RCAs, known failure modes, and engineering knowledge retrieval. |
| Integrated agent-team workflow | Planned | Reliability Agent coordinates Master Data, Defect Elimination, Strategy, and Reliability Improvement agents into a consolidated final recommendation. |
| Reporting and roadmap outputs | Planned | Generate monthly reliability reports, opportunity pipelines, prioritized action plans, and reliability roadmaps. |
| Production readiness | Planned | Add authentication, authorization, file storage hardening, observability, background jobs, deployment configuration, and robust error handling. |
