# Agent Architecture

## Reliability Manager Agent (Orchestrator)

### Purpose

Act as the Reliability Manager.

The Reliability Manager Agent receives user requests, determines which specialist agents are required, delegates work, executes shared analysis tools, consolidates findings, and generates the final recommendation.

The Reliability Manager is the only agent visible to the user.

---

# Specialist Agents

## 1. Master Data Wizard Engineer

### Purpose

Prepare, clean, validate, and standardize uploaded data.

### Tools

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

## 2. Defect Elimination Engineer

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

## 3. Strategy Engineer

### Purpose

Review and optimize maintenance strategies.

### Tools

* PM frequency analysis
* PM effectiveness check
* Corrective vs preventive ratio
* Over-maintenance detection
* Missing PM detection
* Strategy summariser
* Spares and cost analysis
* Condition monitoring recommendations
* FMEA control review
* OEM recommendations
* Strategy gap analysis
* Failure mode coverage analysis

### Outputs

* Keep PM tasks
* Modify PM tasks
* Delete PM tasks
* Recommended frequencies
* Missing PM recommendations
* Condition monitoring opportunities
* Strategy gaps

---

## 4. Reliability Improvement Engineer

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
Reliability Manager Agent
  ↓
Master Data Wizard Agent
  ↓
Reliability Manager Agent
  ↓
Specialist Agents:
  - Defect Elimination Engineer
  - Strategy Engineer
  - Reliability Improvement Engineer
  ↓
Reliability Manager Agent
  ↓
Final response/report
```

---

# Agent Structure

Reliability Manager Agent
│
├── Master Data Wizard Agent
│   └── data mapping + validation tools
│
├── Defect Elimination Engineer
│   └── RCA + repeat failure tools
│
├── Strategy Engineer
│   └── PM review tools
│
└── Reliability Improvement Engineer
    └── value/risk/report tools


```
```
