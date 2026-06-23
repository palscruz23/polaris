# Planned Agent Architecture

This workflow describes the planned multi-agent product architecture. The
current backend supports the user-facing Reliability Agent chat with persistent
conversations, message history, provider-backed responses, conversation memory,
and a bounded sequential multi-call orchestration loop. The Master Data, Defect
Elimination, and Maintenance Strategy agents are registered specialists;
additional specialists remain planned increments.

## Reliability Agent (Orchestrator)

### Purpose

Act as the Reliability Agent.

The Reliability Agent receives user requests, determines which specialist
agents are required, delegates work, reviews structured findings from those
specialist agents, consolidates findings, and generates the final
recommendation.

The Reliability Agent is the only agent visible to the user.

### Agent and Tool Responsibilities

The architecture separates orchestration, specialist reasoning, and
deterministic tool execution.

```text
Reliability Agent
  Owns the user conversation, assesses intent, selects specialist agents,
  and consolidates specialist findings into the final answer.

Specialist Agent
  Owns a reliability workflow such as master data preparation, defect
  elimination, strategy review, or improvement planning. It decides which of
  its own tools to use and returns structured findings to the Reliability Agent.

Tool
  Performs a focused calculation, retrieval, validation, or report-building
  task. Tools do not decide the user-facing answer; they provide evidence and
  computed results for agents to reason over.
```

The Reliability Agent should not directly perform every specialist
calculation. For example, when the user asks for repeat failure analysis, the
Reliability Agent should call the Defect Elimination Agent. The Defect
Elimination Agent then uses its own tools, such as bad actor analysis, repeat
failure detection, MTBF/MTTR calculation, and charter generation. The Defect
Elimination Agent returns structured findings to the Reliability Agent, and the
Reliability Agent consolidates the final response to the user.

The chat streams transient operational progress while this workflow runs. These
events describe coordination and named analysis stages, such as failure-mode
coverage or bad actor analysis. They are not stored as conversation messages
and do not expose private model reasoning.

---

# Specialist Agents

## 1. Master Data Agent

### Purpose

Provide trusted equipment-master discovery now, then prepare, clean, validate,
and standardize uploaded data in later workflows.

### Implemented Tools

* Equipment master listing
* Equipment text search
* Equipment type, location, criticality, and status filters
* Bounded pagination
* Matching status and equipment-type summary counts

### Planned Tools

* File type detection
* Dataset type detection
* Data preview
* Column semantic description capture
* Agent-assisted column description suggestion
* Column description review and approval
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

### Work Order Upload Workflow

The first Master Data Agent workflow should prepare uploaded work order data
for reliable downstream analysis. The workflow must establish the semantic
meaning of each source column before suggesting mappings to the reliability
data model.

```text
User uploads work order file
  ↓
Master Data Agent detects file type, dataset type, headers, sample values,
row count, and basic column quality
  ↓
User chooses column description mode:
  - Manually describe each column
  - Ask Master Data Agent to suggest column descriptions
  ↓
User reviews, edits, and approves every column description
  ↓
Master Data Agent suggests reliability-model column mappings using both
header names and approved semantic descriptions
  ↓
User reviews and confirms mappings
  ↓
Master Data Agent validates required fields, dates, duplicate records,
equipment references, and other import-readiness checks
  ↓
Master Data Agent produces clean work order data, a data quality report,
and a data readiness score
```

Column descriptions capture what the column means in the user's source system,
not just what the header says. For example, a column named `Equip` may be
described as "equipment identifier used to link work orders to the asset
register", while `ShortText` may be described as "free-text maintenance problem
or task description".

Agent-generated descriptions are suggestions only. The user must review and
approve or edit them before mapping, validation, or import can proceed. This
keeps the workflow useful while avoiding silent assumptions about site-specific
maintenance data.

Key design principle: AI can suggest semantic meaning, but the user owns
confirmation before the data becomes trusted reliability input.

---

## 2. Defect Elimination Agent

### Purpose

Convert reliability issues into structured investigations.

### Tools

* Bad actor analysis
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

* Bad actor shortlist
* Repeat failure groups
* MTBF and MTTR metrics
* Defect elimination charter
* Problem statement
* Failure hypotheses
* Required evidence
* Root cause investigation plan
* Recommended corrective actions

### Specialist Workflow

```text
Reliability Agent requests defect elimination insight
  ↓
Defect Elimination Agent interprets the reliability problem
  ↓
Defect Elimination Agent selects and executes its tools:
  - Bad actor analysis
  - Work order history summarisation
  - Repeat failure detection
  - MTBF calculation
  - MTTR calculation
  - Known failure mode retrieval
  - RCA evidence checklist or charter generation
  ↓
Defect Elimination Agent returns structured findings:
  - Ranked bad actors
  - Evidence summary
  - Repeat failure patterns
  - Reliability metrics
  - Hypotheses and required evidence
  - Recommended next actions
  ↓
Reliability Agent consolidates findings into the user-facing response
```

---

## 3. Maintenance Strategy Agent

### Purpose

Review and optimize maintenance strategies.

### Implemented Tools

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

The v1 agent does not recommend deleting tasks or claim causal PM
effectiveness. Task completion, schedule compliance, OEM, FMEA, statutory,
labor-hour, and spares data are not yet represented in the reliability model.

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
Reliability Agent assesses intent and required expertise
  ↓
Reliability Agent delegates to one or more specialist agents:
  - Master Data Agent
      └── Uses mapping, validation, cleaning, and readiness tools
  - Defect Elimination Agent
      └── Uses bad actor, repeat failure, MTBF/MTTR, RCA, and charter tools
  - Maintenance Strategy Agent
      └── Uses PM review, frequency, effectiveness, and coverage tools
  - Reliability Improvement Agent
      └── Uses value, risk, ranking, action-plan, and reporting tools
  ↓
Specialist agents return structured findings to the Reliability Agent
  ↓
Reliability Agent consolidates evidence, resolves conflicts, and decides
the user-facing recommendation
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
