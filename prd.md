# PRD UPDATE: RELIABILITY KNOWLEDGE BASE

## New Product Positioning

Open Reliability Copilot is an AI-powered reliability engineering platform that combines:

1. Work Order Intelligence
2. Maintenance Strategy Intelligence
3. Reliability Knowledge Intelligence

to create a digital team of reliability engineers.

---

## Architecture:
Frontend: Next.js 
Backend: FastAPI 
Database: Postgres 
Vector DB: pgvector

For local development, include everything in Docker compose.

# Updated Core Product Pillars

## Pillar 1: Work Order Intelligence

Understand what happened.

Inputs:

* Work Orders
* Notifications
* Downtime
* Costs
* Failure Codes

Outputs:

* Bad Actors
* Failure Trends
* Repeat Failures

---

## Pillar 2: Strategy Intelligence

Understand what maintenance exists.

Inputs:

* PM Tasks
* Strategies
* Maintenance Plans

Outputs:

* Strategy Optimization
* PM Effectiveness
* Maintenance Gaps

---

## Pillar 3: Reliability Knowledge Intelligence

Understand what engineers know.

Inputs:

* FMEA
* RCA Reports
* OEM Manuals
* Maintenance Standards
* Inspection Standards
* Lubrication Standards
* Failure Reports
* Shutdown Reports
* Reliability Standards

Outputs:

* Failure Mode Intelligence
* Best Practices
* Lessons Learned
* Recommended Actions

---

# New Feature 7: Reliability Knowledge Base

## Objective

Provide a searchable engineering knowledge repository that augments reliability analysis.

The Knowledge Base allows the AI agents to use engineering documentation in addition to work order history.

---

# Supported Documents

## Reliability Documents

* FMEA
* RCM Analysis
* Criticality Assessments
* Failure Mode Libraries

## Maintenance Documents

* Maintenance Strategies
* PM Procedures
* Lubrication Procedures
* Inspection Procedures

## OEM Documents

* OEM Manuals
* Technical Bulletins
* Service Bulletins

## Investigation Documents

* RCA Reports
* Defect Elimination Reports
* Incident Investigations

## Site Standards

* Reliability Standards
* Asset Management Standards
* Maintenance Standards

---

# User Workflow

Step 1

Upload documents

Step 2

Documents indexed

Step 3

Embeddings created

Step 4

Knowledge linked to equipment

Step 5

Agents use knowledge during analysis

---

# Knowledge Base Architecture

## Local Deployment

Storage

```text
uploads/knowledge/
```

Database

```text
Postgres
```

Vector Extension

```text
pgvector
```

Postgres stores both document metadata and vector embeddings. The pgvector
extension provides similarity search for document chunks.

Docker Compose will be added after the initial frontend and backend scaffolds
are developed, so the Compose setup can reflect the actual application services.

---

# Knowledge Base Data Model

## Documents

* document_id
* title
* document_type
* equipment_type
* upload_date

## Chunks

* chunk_id
* document_id
* content
* embedding

## Equipment Links

* equipment_id
* document_id

---

# MCP Server Additions

## Tool: search_knowledge_base

Search reliability knowledge.

Inputs

* query

Outputs

* relevant documents

---

## Tool: retrieve_failure_modes

Retrieve known failure modes.

Inputs

* equipment type

Outputs

* failure mode library

---

## Tool: retrieve_best_practices

Retrieve engineering best practices.

Inputs

* equipment type

Outputs

* recommendations

---

## Tool: retrieve_rca_history

Retrieve previous investigations.

Inputs

* equipment

Outputs

* related RCAs

---

## Tool: build_failure_mode_library

Generate failure mode catalogue.

Outputs

* failure modes
* causes
* controls

---

# Agent Enhancements

## Bad Actor Engineer

Previously:

Used only work orders.

Now:

Uses

* Work Orders
* Knowledge Base

Can explain WHY failures occur.

---

## Defect Elimination Engineer

Previously:

Used only failure history.

Now:

Uses

* Failure history
* RCA reports
* FMEA
* OEM recommendations

Generates stronger investigations.

---

## Strategy Engineer

Previously:

Used only PM data.

Now:

Uses

* PM strategy
* OEM manuals
* Existing standards

Provides evidence-backed recommendations.

---

## Equipment Intelligence Engineer

Previously:

Equipment profile.

Now:

Equipment digital twin.

Includes:

* Work order history
* Strategy
* Known failure modes
* OEM recommendations
* Previous investigations
* Best practices

---

## Reliability Improvement Manager

Previously:

Aggregated findings.

Now:

Builds reliability improvement roadmap using:

* Work Orders
* Strategies
* Knowledge Base

---

# New Feature: Equipment Intelligence 2.0

Equipment Intelligence becomes the flagship feature.

For any asset:

Example:

```text
Cyclone Feed Pump P-101
```

The system automatically generates:

## Asset Summary

Description

Criticality

Strategy Summary

## Failure History

Top Failures

Cost

Downtime

MTBF

## Known Failure Modes

From:

* FMEA
* OEM manuals
* RCA reports

## Existing Controls

Current PMs

Inspections

Monitoring

## Improvement Opportunities

Defect Elimination

Strategy Changes

Condition Monitoring

## Reliability Score

0–100 score

---

# Future Feature: Reliability Knowledge Graph

## Objective

Connect relationships between:

Equipment

Failure Modes

Strategies

RCA Reports

Work Orders

Recommendations

Example

```text
Cyclone Feed Pump

→ Mechanical Seal Failure

→ Appears in 35 Work Orders

→ Referenced in 2 RCAs

→ Covered by PM-001

→ OEM Bulletin 2024-05
```

This becomes the foundation for future autonomous reliability agents.

---

# Updated MVP Scope

Included

* Data Mapping Wizard
* Work Order Analysis
* Strategy Analysis
* Bad Actor Analysis
* Equipment Intelligence
* Reliability Knowledge Base
* Defect Elimination
* Reliability Recommendations
* MCP Server
* Multi-Agent System
* OpenAI Support
* DeepSeek Support

Excluded

* SAP Direct Integration
* Maximo Integration
* Multi-user Collaboration
* Stripe Billing
* Cloud Hosting

---

# Product Moat

Most AI maintenance tools only analyze work orders.

Open Reliability Copilot combines:

1. Work Orders
2. Maintenance Strategies
3. Engineering Knowledge

This allows the AI to think more like a reliability engineer rather than a reporting tool.

The long-term vision is to create a digital reliability engineering team capable of analyzing plant history, understanding engineering standards, and recommending reliability improvements with supporting evidence.
