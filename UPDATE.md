# Proposal: Updating the Workshop to Use the Manufacturing Data Model

This document describes how to update the existing AWS + Neo4j GraphRAG workshop from a **SEC 10-K financial filings** domain to an **automotive manufacturing** domain using the new data model provided in `TransformedData/`.

---

## Part 1: Data Model Overview

### What the Data Model Represents

The new data model represents a **product development and quality assurance workflow** for an automotive manufacturing company. It tracks how a vehicle product (codenamed "R2D2", a robot) moves from high-level product requirements through component design, testing, and change management. The domain is centered around a high-voltage battery system for an electric powertrain.

### Nodes (Entities)

The data model contains the following node types:

| Node Label | Description | Key Properties | CSV Source |
|------------|-------------|----------------|------------|
| **Product** | A vehicle or product under development | product_id, Product Name, Description | `products.csv` |
| **TechnologyDomain** | A technology area within a product (e.g., Electric Powertrain) | technology_domain_id, Technology Domain | `technology_domains.csv` |
| **Component** | A specific hardware component (e.g., HVB_3900 high-voltage battery) | component_id, Component, Component Description | `components.csv` |
| **Requirement** | An engineering requirement with bilingual descriptions (German/English) | requirement_id, Requirement, Description, Type (HW/SW), Vehicle Project, Technology Cluster | `requirements.csv` |
| **TestSet** | A group of related test cases for validating a requirement | test_set_id, Test Set | `test_sets.csv` |
| **TestCase** | An individual test with schedule, duration, status, and assigned responsibility | Test Case ID, Test Case, Test Status, Resources, Test Duration, Start/End Date, Responsibility, I-Stage | `test_cases.csv` |
| **Defect** | A defect found during testing with severity, priority, and resolution tracking | defect_id, Description, Severity, Priority, Assigned To, Status, Creation/Resolved Date | `defects.csv` |
| **Change** | A change proposal triggered by defects or evolving requirements | change_proposal_id, Description, Criticality, Development Cost, Production Cost, Status, Urgency, Risk | `changes.csv` |
| **Milestone** | A project milestone with a deadline | milestone_id, Deadline | `milestones.csv` |
| **MaturityLevel** | Referenced in the diagram; represents development maturity stages (I-Stages seen in test cases) | (implied from test case I-Stage values) | (derived) |
| **Resource** | Referenced in the diagram; represents test resources (labs, instruments, personnel) | (implied from test case Resources field) | (derived) |

### Relationships

The relationships form a traceability chain from product definition through testing to defect resolution:

| Relationship | From | To | Description | CSV Source |
|-------------|------|----|-------------|------------|
| **PRODUCT_HAS_DOMAIN** | Product | TechnologyDomain | A product contains technology domains | `product_technology_domains.csv` |
| **DOMAIN_HAS_COMPONENT** | TechnologyDomain | Component | A domain contains components | `technology_domains_components.csv` |
| **COMPONENT_HAS_REQ** | Component | Requirement | A component has engineering requirements | `components_requirements.csv` |
| **TESTED_WITH** | Requirement | TestSet | A requirement is validated by test sets | `requirements_test_sets.csv` |
| **CONTAINS_TEST_CASE** | TestSet | TestCase | A test set contains individual test cases | `test_sets_test_cases.csv` |
| **DETECTED** | TestCase | Defect | A test case detected a defect | `test_case_defect.csv` |
| **CHANGE_AFFECTS_REQ** | Change | Requirement | A change proposal affects requirements | `changes_requirements.csv` |
| **REQUIRES_ML** | Requirement | MaturityLevel | A requirement targets a maturity level | (diagram) |
| **ML_FOR_REQ** | MaturityLevel | Requirement | Reverse of maturity level mapping | (diagram) |
| **REQUIRES_FLAWLESS_TEST_SET** | Requirement | TestSet | Requirement needs flawless test set results | (diagram) |
| **REQUIRES** | TestCase | Resource | A test case requires specific resources | (diagram) |
| **NEXT** | Milestone | Milestone | Sequential ordering of milestones | (diagram) |
| **REQUIRES_ML** | Requirement-TestSet-Milestone | (join table) | Links requirements, test sets, and milestones | `requirements_test_sets_milestone.csv` |

### What Makes This Domain Interesting for GraphRAG

1. **Traceability chains**: The graph enables end-to-end traceability from a product down to individual defects, which is a core concern in automotive manufacturing (ISO 26262, ASPICE).
2. **Impact analysis**: When a change proposal is raised, the graph can trace which requirements, test sets, and components are affected.
3. **Bilingual content**: Requirements have both German ("Anforderung"/"Beschreibung") and English descriptions, offering a natural use case for multilingual embeddings and search.
4. **Rich structured data**: Unlike the original SEC filings (unstructured text), this dataset is fully structured with explicit relationships, making it ideal for Text2Cypher and graph traversal queries.
5. **Real-world manufacturing concerns**: Defect tracking, change cost analysis, and milestone planning are questions manufacturing engineers actually ask.

---

## Part 2: Lab-by-Lab Update Plan

### Lab 0 (Sign In) — No Changes

This lab covers AWS sign-in and is domain-independent.

### Lab 1 (Aura Setup) — Backup File and Explore Patterns

**What changes:**

- **Backup file**: Replace `finance_data.backup` with a new backup built from the manufacturing data. The backup should contain all nodes and relationships from the CSV files, with embeddings pre-generated on Requirement and Defect description text.
- **README.md**: Update the description of what the backup contains. Replace references to "SEC 10-K filings", "companies", "risk factors", "asset managers" with "manufacturing product data", "components", "requirements", "defects", "change proposals".
- **EXPLORE.md**: Replace the exploration patterns entirely:
  - Instead of `AssetManager — OWNS → Company — FACES_RISK → RiskFactor`, use patterns like:
    - `Product — PRODUCT_HAS_DOMAIN → TechnologyDomain — DOMAIN_HAS_COMPONENT → Component`
    - `Component — COMPONENT_HAS_REQ → Requirement — TESTED_WITH → TestSet — CONTAINS_TEST_CASE → TestCase — DETECTED → Defect`
    - `Change — CHANGE_AFFECTS_REQ → Requirement`
  - Update the Degree Centrality walkthrough to highlight which requirements have the most test cases, or which components have the most defects.
  - Update all screenshots to reflect the manufacturing graph.

### Lab 2 (Aura Agents) — Prompt and Schema Updates

**What changes:**

- Update the agent prompts and any example questions to reference manufacturing entities (requirements, defects, test cases) instead of financial entities (companies, risk factors, asset managers).

### Lab 3 (Bedrock Setup) — No Changes

This lab covers AWS Bedrock configuration and is domain-independent.

### Lab 5 (Start Codespace) — No Changes

This lab covers environment setup and is domain-independent.

### Lab 6 (Knowledge Graph) — Major Rewrite

This lab is the most heavily impacted because it builds the graph from scratch using sample data.

**01_data_loading.ipynb — Replace sample data and graph structure**

- Replace the Apple 10-K sample text with manufacturing content. Use the Requirement descriptions from `requirements.csv` as the source text (they are detailed engineering specifications that chunk well).
- Replace the `(:Document) <-[:FROM_DOCUMENT]- (:Chunk) -[:NEXT_CHUNK]-> (:Chunk)` structure with loading from CSVs. The notebook should demonstrate:
  - Creating Product, TechnologyDomain, and Component nodes from their respective CSVs.
  - Creating the PRODUCT_HAS_DOMAIN, DOMAIN_HAS_COMPONENT relationships.
  - This teaches the same fundamentals (creating nodes, creating relationships) but with the new domain.
- Update all explanatory markdown to describe manufacturing traceability instead of document chunking.

**02_embeddings.ipynb — Embed requirement descriptions**

- Instead of chunking an Apple 10-K filing, generate embeddings for Requirement description text and Defect description text.
- The vector index should be on Requirement nodes (property: `embedding`) or on Chunk nodes created from requirement text.
- Update the sample search queries from "What products does Apple make?" to domain-appropriate queries like:
  - "What are the thermal management requirements?"
  - "Which requirements relate to energy density?"
  - "What battery safety requirements exist?"
- Keep the same teaching structure (FixedSizeSplitter, BedrockEmbeddings, vector index, similarity search) but with manufacturing content.

**03_entity_extraction.ipynb — Extract manufacturing entities**

- Replace the Company/Product/Service schema with entities relevant to the manufacturing domain. Since the data is already structured, this notebook should demonstrate entity extraction from the *text descriptions* in requirements and defects. Possible schema:
  - Entity types: `TechnicalConcept`, `Material`, `Specification`, `SafetyStandard`, `TestMethod`
  - Relationship types: `SPECIFIES`, `USES_MATERIAL`, `COMPLIES_WITH`, `MEASURED_BY`
  - This extracts implicit knowledge from the requirement descriptions that is not captured in the explicit CSV structure.
- Update the SimpleKGPipeline schema definition and all example queries.

**04_full_dataset.ipynb — Load and explore full manufacturing dataset**

- Replace the SEC filings backup exploration with queries against the full manufacturing graph.
- Replace all example queries:
  - Instead of "What products does Apple make?" → "What components does the R2D2 product use?"
  - Instead of "What are the main risk factors?" → "What are the open defects with high severity?"
  - Instead of company/risk factor exploration → component/requirement/defect exploration.
- Update the data model documentation in the notebook to show the manufacturing schema.

### Lab 7 (Retrievers) — Query and Schema Updates

**01_vector_retriever.ipynb**

- Update the vector index name if it changes (or keep `chunkEmbeddings` if embeddings are still on Chunk nodes).
- Replace all example queries:
  - "What are the risks that Apple faces?" → "What are the thermal management requirements for the battery?"
  - "What products does Microsoft reference?" → "What test cases are planned for cell design?"
  - "What warnings have Nvidia given?" → "What defects have been found in the high-voltage battery?"
- Update the GraphRAG system prompt context to reference manufacturing data.

**02_vector_cypher_retriever.ipynb**

- Replace the `asset_manager_query` Cypher with manufacturing-domain traversals. Examples:
  - From a matched Chunk, traverse to the Requirement, then to the Component and its TestSets.
  - From a matched Chunk, find related Change proposals and their cost/risk information.
- Replace the `shared_risks_query` with a manufacturing equivalent, such as finding requirements that share defects or components affected by the same change proposal.
- Update all example questions.

**03_text2cypher_retriever.ipynb**

- The Text2Cypher prompt needs the new schema (it auto-detects via `get_schema(driver)` so the prompt template itself may not need changes).
- Replace all example queries:
  - "What companies are owned by BlackRock?" → "What requirements does the HVB_3900 component have?"
  - "How many risk factors does Apple face?" → "How many defects have high severity?"
  - "Which asset managers own both Apple and Amazon?" → "Which requirements are affected by change proposal CP001?"

### Lab 8 (Agents) — Tool Descriptions and Queries

**01_simple_agent.ipynb**

- Update the system prompt from "SEC 10-K financial filings" to "automotive manufacturing product development data".
- Update example questions from schema exploration of financial entities to manufacturing entities.

**02_vector_graph_agent.ipynb**

- Update the `retrieval_query` Cypher from the financial graph traversal (`FILED`, `FACES_RISK`) to manufacturing traversals (`COMPONENT_HAS_REQ`, `TESTED_WITH`, `DETECTED`).
- Update the `retrieve_financial_documents` tool to `retrieve_manufacturing_data` with an updated docstring describing manufacturing search use cases.
- Update the system prompt and all example queries.

**03_text2cypher_agent.ipynb**

- Same changes as the vector graph agent: update retrieval queries, tool names/docstrings, system prompts, and example questions.
- Update the Text2Cypher prompt if it has hardcoded schema references.
- Replace all financial domain example queries with manufacturing queries like:
  - "What requirements are affected by change proposals?"
  - "Which test cases have detected defects?"
  - "What is the development cost of open change proposals?"

### Lab 9 (Hybrid Search) — Index Names and Queries

**01_fulltext_search.ipynb**

- Create a fulltext index on manufacturing entity names (Requirement names, Component names, Defect descriptions) instead of the `search_entities` index on Company/Product/RiskFactor names.
- Replace all search examples:
  - Basic search: "Battery" instead of "Apple"
  - Fuzzy search: "Battrey~" instead of "Aplle~"
  - Wildcard: "HVB*" instead of "Micro*"
  - Boolean: "thermal AND management" instead of "supply NOT chain"
- Update the graph traversal example to traverse from a found Component to its Requirements and Defects.

**02_hybrid_search.ipynb**

- Update both the vector index name and fulltext index name references.
- Replace the `RETRIEVAL_QUERY` Cypher from financial traversals (`FILED`, `FACES_RISK`, `MENTIONS`) to manufacturing traversals.
- Update all example queries and alpha-tuning demonstrations to use manufacturing terms.

---

## Part 3: Data Preparation Work

Before the lab updates can proceed, the following data preparation is needed:

1. **CSV data loading script**: Write a Cypher script or Python notebook that loads all 18 CSV files into Neo4j with the correct node labels, properties, and relationships. This becomes the new "full dataset" loading approach.

2. **Embeddings generation**: Generate embeddings for text-rich fields:
   - Requirement `Description` (English) — primary embedding target
   - Defect `Description` — secondary embedding target
   - Change `Description` — secondary embedding target
   - Optionally chunk longer descriptions and embed the chunks.

3. **Backup file creation**: After loading the full dataset with embeddings, export a Neo4j backup file to replace `finance_data.backup`.

4. **Fulltext index creation**: Create fulltext indexes on relevant text properties for hybrid search support.

5. **Vector index creation**: Create vector indexes on the embedded properties.

6. **MaturityLevel and Resource nodes**: The diagram references MaturityLevel and Resource as explicit nodes, but the CSV data embeds these as properties within test cases (I-Stage and Resources columns). Decide whether to extract these into separate nodes or keep them as properties. Extracting them would create a richer graph for traversal demonstrations.

---

## Part 4: What Stays the Same

The following aspects of the workshop remain unchanged:

- **AWS infrastructure**: Bedrock setup, credential configuration, Codespace environment.
- **Neo4j Aura setup**: The signup and provisioning flow is identical regardless of domain.
- **Python libraries**: neo4j-graphrag, Strands SDK, BedrockEmbeddings, BedrockLLM all work the same way.
- **Teaching patterns**: The pedagogical flow (data loading → embeddings → entity extraction → retrievers → agents → hybrid search) is preserved.
- **Code structure**: The `config.py` module, notebook cell structure, and import patterns stay the same.
- **Core concepts**: Vector search, Text2Cypher, VectorCypherRetriever, HybridRetriever, Strands agents — all concepts are taught identically, just with different domain data and queries.
