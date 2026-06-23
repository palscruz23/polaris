# PRD: Open Reliability Product Vision

## Current Implementation State

The current product includes the user-facing Reliability Agent chat, FastAPI
conversation endpoints, PostgreSQL-backed conversation and message persistence,
provider-backed assistant responses, deterministic conversation titles,
per-conversation memory updates, bounded specialist orchestration, and
implemented Master Data equipment discovery, Defect Elimination, and
Maintenance Strategy specialist workflows.

The multi-agent workflows below describe the product direction. Master Data
upload and mapping, Reliability Improvement, knowledge-base, and
pgvector-backed retrieval capabilities remain planned unless explicitly marked
as implemented elsewhere.

## New Product Positioning

Open Reliability Copilot is an AI-powered reliability engineering platform that combines:

1. Work Order Intelligence
2. Maintenance Strategy Intelligence
3. Reliability Knowledge Intelligence

to create a digital team of reliability engineers.

---

## Target Architecture

Frontend: Next.js
Backend: FastAPI
Database: Postgres
Vector DB: pgvector

For local development, include everything in Docker compose.

Conversation sessions, PostgreSQL message persistence, model-agnostic context
selection using provider token budgets, and per-session `memory.md` behavior are defined in
[`conversation-memory.md`](conversation-memory.md).

# Agent Architecture

## Reliability Agent (Orchestrator)

### Purpose

Act as the Reliability Agent.

The Reliability Agent receives user requests, determines which specialist agents are required, delegates work, executes shared analysis tools, consolidates findings, and generates the final recommendation.

The Reliability Agent is the only agent visible to the user.

---

# Specialist Agents

## 1. Master Data Agent

### Purpose

Provide trusted equipment-master discovery now, then prepare, clean, validate,
and standardize uploaded data in later workflows.

### Implemented Tools

* Equipment master listing and search
* Equipment type, location, criticality, and status filters
* Bounded pagination and matching summary counts

### Planned Tools

* File type detection
* Dataset type detection
* Data preview
* Column mapping suggestion
* Column mapping validation
* Date normalization
* Numeric field cleaning
* Duplicate record detection
* Equipment ID validation
* Work order linking
* Strategy linking
* Failure mode classification
* Data quality scoring
* Import validation
* Mapping template management

### Outputs

* Clean work orders
* Clean equipment master
* Clean strategy data
* Data quality report
* Data readiness score

---

## 2. Defect Elimination Agent

### Purpose

Convert reliability issues into structured investigations.

### Tools

* Equipment profile builder
* Known failure modes retrieval
* WO history summariser
* Repeat failure detection
* MTBF calculation
* MTTR calculation
* 5 Whys generator
* RCA template builder
* Failure mode clustering
* Similar WO search
* Previous RCA search
* Corrective action tracker
* Defect elimination charter generator

### Outputs

* Defect elimination charter
* Problem statement
* Failure hypotheses
* Required evidence
* Root cause investigation plan
* Recommended corrective actions

---

## 3. Maintenance Strategy Agent

### Purpose

Review and optimize maintenance strategies.

### Tools

* Maintenance strategy profile builder
* Maintenance mix analyzer
* Failure mode coverage analyzer
* Frequency risk analyzer
* Maintenance strategy gap detector
* Condition monitoring opportunity analyzer
* Maintenance strategy recommendation builder

### Outputs

* Keep, modify, add, or engineering-review recommendations
* Frequency risk flags
* Missing or partial failure-mode coverage
* Condition monitoring opportunities
* Strategy gaps

---

## 4. Reliability Improvement Agent

### Purpose

Convert engineering findings into business actions.

### Tools

* Agent findings consolidator
* Opportunity value estimator
* Cost-benefit analysis
* Risk scoring
* Opportunity ranking
* Action plan builder
* Opportunity pipeline builder
* Monthly report generator
* Reliability roadmap generator
* Executive summary generator

### Outputs

* Monthly reliability report
* Opportunity pipeline
* Estimated value
* Prioritized action plan
* Reliability roadmap
* Executive summary

---

# Updated Workflow

```text
User
  ↓
Reliability Agent
  ↓
Master Data Agent
  ↓
Reliability Agent
  ↓
Specialist Agents:
  - Defect Elimination Agent
  - Maintenance Strategy Agent
  - Reliability Improvement Agent
  ↓
Reliability Agent
  ↓
Final response/report
```

---

# Agent Structure

Reliability Agent
│
├── Master Data Agent
│   └── data mapping + validation tools
│
├── Defect Elimination Agent
│   └── RCA + repeat failure tools
│
├── Maintenance Strategy Agent
│   └── PM review tools
│
└── Reliability Improvement Agent
    └── value/risk/report tools
