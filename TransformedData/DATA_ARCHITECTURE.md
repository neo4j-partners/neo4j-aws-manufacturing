# Manufacturing Data Architecture

This document describes the graph data model for the automotive manufacturing workshop dataset. The model represents a **product development and quality assurance workflow** for an electric vehicle program (codenamed "R2D2"), tracking the full lifecycle from product definition through component design, requirements engineering, testing, defect resolution, and change management.

<!-- DIAGRAM: Manufacturing Data Model -->
![Manufacturing Data Model](manufacturing-data-model.png)

---

## Node Types

### Product
The top-level entity representing a vehicle program under development.

| Property | Type | Example |
|----------|------|---------|
| product_id | Integer | `1` |
| Product Name | String | `R2D2` |
| Description | String | `Robot` |

**Source**: `products.csv` (1 record)

### TechnologyDomain
A major technology area within a product, grouping related components.

| Property | Type | Example |
|----------|------|---------|
| technology_domain_id | Integer | `1` |
| Technology Domain | String | `Electric Powertrain` |

**Source**: `technology_domains.csv` (4 records: Electric Powertrain, Chassis, Body, Infotainment)

### Component
A specific hardware subsystem or module within a technology domain.

| Property | Type | Example |
|----------|------|---------|
| component_id | Integer | `1` |
| Component | String | `HVB_3900` |
| Component Description | String | `High-Voltage Battery` |

**Source**: `components.csv` (8 records including HVB_3900, PDU_1500, INV_2300, etc.)

### Requirement
An engineering requirement specification with bilingual content (German/English). This is the richest text node and the primary target for embeddings.

| Property | Type | Example |
|----------|------|---------|
| requirement_id | String | `1_1` |
| Anforderung | String | `Batteriezellen- und Moduldesign` (German title) |
| Requirement | String | `Battery Cell and Module Design` (English title) |
| Beschreibung | String | German description |
| Description | String | English description (detailed engineering spec) |
| Vehicle Project | String | `R2D2` |
| Technology Cluster | String | `Electric Powertrain` |
| Component | String | `HVB_3900` |
| Type | String | `HW` or `SW` |

**Source**: `requirements.csv`

### TestSet
A logical grouping of related test cases that validate a requirement.

| Property | Type | Example |
|----------|------|---------|
| test_set_id | String | `TS_1_1` |
| Test Set | String | `Cell Design Tests` |

**Source**: `test_sets.csv`

### TestCase
An individual test with scheduling, resource, and status information.

| Property | Type | Example |
|----------|------|---------|
| Test Case ID | String | `TC_1_1_1` |
| Test Case | String | `Voltage` |
| Test Status | String | `Planned`, `Passed`, `Failed` |
| Resources | String | `Test lab measuring instruments` |
| Test Duration (hours) | Integer | `48` |
| Start Date | Date | `06/15/2023` |
| End Date | Date | `06/17/2023` |
| Responsibility | String | `Battery Cell Engineer` |
| I-Stage | String | `I-300` |

**Source**: `test_cases.csv`

### Defect
A defect discovered during testing, with severity, priority, and resolution tracking.

| Property | Type | Example |
|----------|------|---------|
| defect_id | String | `DEF001` |
| Description | String | `Energy density does not meet specifications` |
| Severity | String | `High`, `Medium`, `Low` |
| Priority | String | `High`, `Medium`, `Low` |
| Assigned To | String | `Battery Cell Engineer` |
| Status | String | `In Progress`, `Resolved` |
| Creation Date | Date | `2024-05-01` |
| Resolved Date | Date | nullable |
| Resolution | String | nullable |
| Comments | String | nullable |

**Source**: `defects.csv`

### Change
A change proposal triggered by defects or evolving requirements, with cost and risk analysis.

| Property | Type | Example |
|----------|------|---------|
| change_proposal_id | String | `CP001` |
| Description | String | `Increase energy density requirement...` |
| Criticality | String | `High`, `Medium`, `Low` |
| Development Cost in USD | Integer | `500000` |
| Production Cost in USD per unit | String | `$2.50` |
| Status | String | `Under Review`, `Approved` |
| Urgency | String | `High`, `Medium`, `Low` |
| Risk | String | Free text risk description |

**Source**: `changes.csv`

### Milestone
A project milestone representing a development gate with a deadline.

| Property | Type | Example |
|----------|------|---------|
| milestone_id | String | `m_100` |
| Deadline | Date | `1/1/26` |

**Source**: `milestones.csv`

### Derived Nodes (from diagram)

The data model diagram also references two additional node types that are derived from properties embedded in test case records:

- **MaturityLevel**: Extracted from the `I-Stage` property on TestCase (e.g., I-300, I-400). Represents development maturity gates.
- **Resource**: Extracted from the `Resources` property on TestCase. Represents test labs, instruments, and personnel.

---

## Relationships

### Product Hierarchy

```
Product --PRODUCT_HAS_DOMAIN--> TechnologyDomain --DOMAIN_HAS_COMPONENT--> Component
```

| Relationship | From | To | Source |
|-------------|------|----|--------|
| PRODUCT_HAS_DOMAIN | Product | TechnologyDomain | `product_technology_domains.csv` |
| DOMAIN_HAS_COMPONENT | TechnologyDomain | Component | `technology_domains_components.csv` |

### Requirements Traceability Chain

```
Component --COMPONENT_HAS_REQ--> Requirement --TESTED_WITH--> TestSet --CONTAINS_TEST_CASE--> TestCase --DETECTED--> Defect
```

| Relationship | From | To | Source |
|-------------|------|----|--------|
| COMPONENT_HAS_REQ | Component | Requirement | `components_requirements.csv` |
| TESTED_WITH | Requirement | TestSet | `requirements_test_sets.csv` |
| CONTAINS_TEST_CASE | TestSet | TestCase | `test_sets_test_cases.csv` |
| DETECTED | TestCase | Defect | `test_case_defect.csv` |

### Change Management

```
Change --CHANGE_AFFECTS_REQ--> Requirement
```

| Relationship | From | To | Source |
|-------------|------|----|--------|
| CHANGE_AFFECTS_REQ | Change | Requirement | `changes_requirements.csv` |

### Milestone and Maturity Tracking

| Relationship | From | To | Source |
|-------------|------|----|--------|
| REQUIRES_ML | Requirement | MaturityLevel | diagram (derived from I-Stage) |
| ML_FOR_REQ | MaturityLevel | Requirement | diagram (reverse mapping) |
| REQUIRES_FLAWLESS_TEST_SET | Requirement | TestSet | diagram |
| REQUIRES | TestCase | Resource | diagram (derived from Resources) |
| NEXT | Milestone | Milestone | diagram (sequential ordering) |

The ternary relationship linking requirements, test sets, and milestones is captured in `requirements_test_sets_milestone.csv`.

---

## Key Traversal Patterns

### End-to-End Traceability (Product to Defect)
```
Product -> TechnologyDomain -> Component -> Requirement -> TestSet -> TestCase -> Defect
```
Answers: "What defects exist for a given product or component?"

### Impact Analysis (Change to affected scope)
```
Change -> Requirement <- Component <- TechnologyDomain <- Product
Change -> Requirement -> TestSet -> TestCase
```
Answers: "Which components and tests are affected by a change proposal?"

### Defect Root Cause (Defect back to Component)
```
Defect <- TestCase <- TestSet <- Requirement <- Component
```
Answers: "Which component is responsible for this defect?"

### Milestone Readiness
```
Milestone <- requirements_test_sets_milestone -> Requirement -> TestSet -> TestCase (check status)
```
Answers: "Are all tests passing for the next milestone?"

---

## Embedding Targets

The following text-rich fields are candidates for vector embeddings to support semantic search and GraphRAG:

| Node | Property | Use Case |
|------|----------|----------|
| Requirement | Description (English) | Primary: semantic search over engineering specs |
| Defect | Description | Secondary: find similar defects, match defects to requirements |
| Change | Description | Secondary: search change proposals by technical concern |
| Requirement | Beschreibung (German) | Multilingual search support |

---

## CSV File Inventory

| File | Type | Records |
|------|------|---------|
| `products.csv` | Node data | Product |
| `technology_domains.csv` | Node data | TechnologyDomain |
| `components.csv` | Node data | Component |
| `requirements.csv` | Node data | Requirement |
| `test_sets.csv` | Node data | TestSet |
| `test_cases.csv` | Node data | TestCase |
| `defects.csv` | Node data | Defect |
| `changes.csv` | Node data | Change |
| `milestones.csv` | Node data | Milestone |
| `product_technology_domains.csv` | Relationship | PRODUCT_HAS_DOMAIN |
| `technology_domains_components.csv` | Relationship | DOMAIN_HAS_COMPONENT |
| `components_requirements.csv` | Relationship | COMPONENT_HAS_REQ |
| `requirements_test_sets.csv` | Relationship | TESTED_WITH |
| `test_sets_test_cases.csv` | Relationship | CONTAINS_TEST_CASE |
| `test_case_defect.csv` | Relationship | DETECTED |
| `changes_requirements.csv` | Relationship | CHANGE_AFFECTS_REQ |
| `requirements_test_sets_milestone.csv` | Ternary join | Requirement + TestSet + Milestone |
