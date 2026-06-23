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
| Open-source licensing | Done | Repository uses the Apache License 2.0 with a project NOTICE file, preserving permissive commercial use while adding explicit patent terms. |
| Deployment runbook | Done | A local gitignored deployment guide documents the Vercel frontend, Render API, Render Postgres, migrations, environment variables, CORS prerequisite, and production smoke test. |
| Reliability Agent chat | Done | User-facing chat experience for reliability engineering questions. |
| Reliability chat route | Done | The canonical chat URL is `/chat-with-reliability`, with redirects from previous chat routes. |
| Chat starter prompt alignment | Done | Suggested questions represent the implemented equipment search, failure analysis, work-order analysis, and maintenance strategy tools. |
| Conversation persistence | Done | Conversations and messages are stored in PostgreSQL with conversation history and session recovery. |
| Conversation memory | Done | Per-session Markdown memory captures durable context for follow-up questions. |
| Provider abstraction | Done | Backend uses a model-provider interface so chat logic is not tightly coupled to one LLM provider. |
| OpenRouter model selection | Done | Chat users can select approved MVP models per message while GPT and Claude options remain visible but disabled for production use; credentials and the model allowlist remain server-controlled. |
| Product-state cleanup | Done | Homepage, README, PRD, and workflow naming now reflect current backend capability and use one agent naming scheme. |
| Tool catalog documentation | Done | README presents tools as concise PascalCase identifiers with short descriptions. |
| Homepage capability messaging | Done | Hero messaging now emphasizes high-level reliability benefits, and the secondary CTA links to the renamed capability roadmap section. |
| Homepage desktop fit pass | Done | Hero and planned architecture sections now use desktop-specific density rules so the main product story fits more comfortably in a desktop viewport. |
| Homepage mobile responsive pass | Done | Hero content, CTAs, benefit panel, and planned architecture diagram now adapt into a narrow-screen vertical layout. |
| Homepage agent status refactor | Done | Agent workflow reflects current orchestration and marks only unimplemented specialists as future capabilities. |
| Chat history default collapse | Done | Reliability Agent chat opens with the conversation history panel collapsed while preserving the existing History toggle. |
| Contact and brand cleanup | Done | Homepage and chat headers use the Open Reliability brand, while the compact centered homepage footer highlights demo and collaboration availability and links to the GitHub repository, issue reporting, and the Apache 2.0 license. |
| Brand logo integration | Done | The provided Open Reliability logo appears beside the product name in the homepage and Reliability Agent headers. |
| Chat Markdown table presentation | Done | Assistant tables render with readable cell spacing, borders, alternating rows, and horizontal scrolling on narrow screens. |
| Master Data Agent v1 | Done | Lists and searches stored equipment with filters for type, location, criticality, and status, bounded pagination, and matching summary counts. Upload, mapping, validation, and data-readiness workflows remain planned. |
| Reliability data model | Done | Normalized backend records now cover equipment, work orders, maintenance strategies, failure modes, import batches, and validation results. |
| Clean data seed loader | Done | Backend CLI loads clean MVP CSV data into the reliability model with import batches, asset links, strategy records, work orders, and failure-mode links. |
| Data Mapping Wizard UI | Planned | Guided frontend workflow for upload, preview, mapping confirmation, validation, and import readiness scoring. |
| Agent tool orchestration | Done | Reliability Agent can select registered specialist capabilities, execute a bounded sequential multi-call loop, suppress duplicate calls, isolate specialist errors, and synthesize a final response from structured findings. |
| Live orchestration progress | Done | Chat streams natural-language progress as the Reliability Agent coordinates specialists, named analysis stages execute, and findings are consolidated into the final persisted response. |
| Defect Elimination Agent v1 | Done | Backend specialist agent and deterministic tools produce MTBF-based bad actor rankings, repeat failure groups, reliability summary metrics, MTBF metrics, Weibull analysis, RCA evidence plans, 5 Whys prompts, RCA templates, defect elimination charters, and recommended next actions through Reliability Agent orchestration. |
| Maintenance Strategy Agent v1 | Done | Reviews maintenance task profiles and work-order mix, assesses observed failure-mode coverage and frequency risks, identifies strategy gaps and condition-monitoring opportunities, and returns bounded keep/modify/add/engineering-review recommendations through Reliability Agent orchestration. |
| Reliability Improvement Agent v1 | Planned | Convert technical findings into ranked opportunities, value estimates, action plans, and executive summaries. |
| Reliability Knowledge Base v1 | Planned | Ingest RCA reports, FMEAs, OEM manuals, site standards, and other documents for retrieval-augmented reliability guidance. |
| pgvector search | Planned | Store document and record embeddings in Postgres with pgvector for similar work orders, previous RCAs, known failure modes, and engineering knowledge retrieval. |
| Integrated agent-team workflow | Planned | Reliability Agent coordinates Master Data, Defect Elimination, Maintenance Strategy, and Reliability Improvement agents into a consolidated final recommendation. |
| Reporting and roadmap outputs | Planned | Generate monthly reliability reports, opportunity pipelines, prioritized action plans, and reliability roadmaps. |
| Production readiness | Planned | Add authentication, authorization, file storage hardening, observability, background jobs, deployment configuration, and robust error handling. |
