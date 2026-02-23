# Workshop Update Plan: SEC 10-K Filings → Manufacturing Domain

This plan describes how to update the workshop to use the automotive manufacturing data model from `TransformedData/`. It covers the main README, then labs 3, 6, 7, 8, and 9 (using the new numbering from UPDATE.md).

**Note on lab numbering:** The current repo has Labs 0, 1, 2, 4, 5, 6, 7. The UPDATE.md proposes a new numbering scheme (Labs 0–9). This plan uses the new numbering. A mapping to current folders is provided where applicable.

---

## Phase 1: Update Main README ✅ COMPLETED

**Goal:** Replace all SEC 10-K / financial domain references with manufacturing domain language throughout the top-level README.md.

### Changes Made

1. ✅ **Overview paragraph** — Replaced "SEC 10-K company filings" with automotive manufacturing dataset description. Describes the traceability chain as the core value proposition.
2. ✅ **Learning objectives list** — Rewritten to reference manufacturing concepts (e.g., "Exploring a manufacturing traceability knowledge graph").
3. ✅ **Quick Start Options** — Kept structure, no numbering changes needed yet.
4. ✅ **Agenda section** — Updated lab descriptions. Removed the "Important Note" about OpenAI vs Titan embedding dimension mismatch (no longer relevant).
5. ✅ **Architecture diagram** — Replaced "SEC 10-K Knowledge Graph" with "Manufacturing Knowledge Graph" showing Products & Components, Requirements & Test Cases, Defects & Change Proposals.
6. ✅ **Knowledge Graph Data Model section** — Fully rewritten:
   - Description paragraph describes R2D2 product, high-voltage battery, electric powertrain
   - Example questions use manufacturing queries
   - Graph Structure diagram shows Product → TechnologyDomain → Component → Requirement → TestSet → TestCase → Defect, plus Change → Requirement
   - Node Types table: Product, TechnologyDomain, Component, Requirement, TestSet, TestCase, Defect, Change, Chunk
   - Relationship Types table: PRODUCT_HAS_DOMAIN, DOMAIN_HAS_COMPONENT, COMPONENT_HAS_REQ, TESTED_WITH, CONTAINS_TEST_CASE, DETECTED, CHANGE_AFFECTS_REQ, HAS_CHUNK, NEXT_CHUNK
   - Search Indexes table: requirement_embeddings (vector), requirement_text (fulltext), search_entities (fulltext)
   - Retrieval Strategies: All four examples updated with manufacturing Cypher
7. ✅ **Resources section** — No changes needed (domain-independent).

---

## Phase 2: Update Lab 3 (Bedrock Setup / Intro to Bedrock and Agents) ✅ COMPLETED

**Currently:** `Lab_4_Intro_to_Bedrock_and_Agents/`

### Changes Made

1. ✅ **load_sample_data.py** — Renamed function to `load_manufacturing_data()` (kept `load_company_data` as backward-compatible alias). Updated default filename to `sample_manufacturing_data.txt`.
2. ✅ **sample_manufacturing_data.txt** — Created new sample data file describing R2D2 product, components, requirements, testing, defects, and change proposals.
3. ✅ **basic_langgraph_agent.ipynb** — Updated:
   - Section 9 title: "Query with Sample Manufacturing Data"
   - Import uses `load_manufacturing_data`
   - Example queries: "What components are in the Electric Powertrain domain?" and "What defects have been found and what are their severities?"
   - Context prompt uses "manufacturing information" instead of "company information"
4. ⬜ **Slides** — Not updated (slides contain domain-independent content about Bedrock/LangGraph; domain-specific slides need screenshot updates which require a running instance).
5. ⬜ **Folder rename** — Not renamed yet (deferred until numbering decision is finalized).

---

## Phase 3: Update Labs 6 and 7 (Knowledge Graph + Retrievers) ✅ COMPLETED

**Currently:** `Lab_5_GraphRAG/`

### Changes Made — data_utils.py ✅

- ✅ Added `CSVLoader` class with `load_csv()` and `load_all()` methods for loading TransformedData CSVs
- ✅ Updated `clear_graph()` to delete all nodes (not just Document/Chunk) since we now have Product, TechnologyDomain, Component, Requirement, Chunk nodes
- ✅ Kept `DataLoader`, `split_text()`, config classes, and AI service functions unchanged

### Changes Made — 01_data_loading.ipynb ✅

1. ✅ **Intro rewritten** — "Data Loading Fundamentals" now teaches manufacturing traceability graph structure instead of Document → Chunk structure
2. ✅ **Sample data** — Loads from TransformedData CSVs (products, technology_domains, components, and relationship CSVs) using `CSVLoader`. Also loads `manufacturing_data.txt` for chunking demo.
3. ✅ **Node creation** — Creates Product, TechnologyDomain, and Component nodes from CSV data (replacing the single Document node)
4. ✅ **Relationship creation** — Creates PRODUCT_HAS_DOMAIN and DOMAIN_HAS_COMPONENT relationships from junction table CSVs
5. ✅ **Chunking** — Splits requirement description text into chunks, creates Requirement node with HAS_CHUNK and NEXT_CHUNK relationships
6. ✅ **Verification** — Updated to show node counts by label, traceability chain, and requirement chunk counts
7. ✅ **manufacturing_data.txt** — Created new sample text file with consolidated HVB_3900 requirement descriptions

### Changes Made — 02_embeddings.ipynb ✅

1. ✅ **Intro rewritten** — Embedding examples use manufacturing terms ("thermal management system cooling" instead of "Apple makes iPhones")
2. ✅ **Sample data** — Loads `manufacturing_data.txt` instead of `company_data.txt`
3. ✅ **Storage** — Creates Requirement node with HAS_CHUNK and NEXT_CHUNK relationships (instead of Document with FROM_DOCUMENT)
4. ✅ **Vector index** — Named `requirement_embeddings` instead of `chunkEmbeddings`
5. ✅ **Search queries** — "What are the thermal management requirements?" instead of "What products does Apple make?"
6. ✅ **Comparison queries** — Energy density specs, water protection, BMS safety monitoring

### Changes Made — 03_vector_retriever.ipynb ✅

1. ✅ **Vector index reference** — Updated to `requirement_embeddings`
2. ✅ **Diagnostic search** — Query: "What are the thermal management requirements for the battery?"
3. ✅ **GraphRAG pipeline** — Same query with manufacturing context
4. ✅ **Experiment queries** — Energy density specifications, BMS safety standards, water ingress protection
5. ✅ **Explanatory markdown** — All references updated from financial to manufacturing domain

### Changes Made — 04_vector_cypher_retriever.ipynb ✅

1. ✅ **Context query** — Traverses from Chunk → Requirement (via HAS_CHUNK) → Component (via COMPONENT_HAS_REQ), plus adjacent chunks via NEXT_CHUNK
2. ✅ **Expanded context query** — Concatenates component name, component description, requirement name, and adjacent chunk text into a single enriched context string
3. ✅ **Example queries** — "What are the cooling requirements for the high-voltage battery?", "What safety standards must the battery system comply with?", "What are the cooling system specifications?"
4. ✅ **Comparison** — Standard VectorRetriever vs VectorCypherRetriever with manufacturing queries
5. ✅ **Summary** — Describes manufacturing traceability traversal as the key differentiator

### Not Yet Done

- ⬜ **Slides** — Not updated (need screenshot updates from running instance)
- ⬜ **Folder split** — Labs 6 and 7 remain in `Lab_5_GraphRAG/` (deferred until numbering decision)
- ⬜ **company_data.txt** — Old file still exists, can be removed once confirmed no longer needed

---

## Phase 4: Update Labs 8 and 9 (Agents + Hybrid Search) ✅ COMPLETED

**Currently:** `Lab_6_Neo4j_MCP_Agent/` and `Lab_7_Aura_Agents_API/`

### Changes Made — Lab 8: Agents

#### Lab 6 README.md ✅

- ✅ Updated "Why Schema Matters" section — Replaced Company/RiskFactor/AssetManager with Product/Component/Requirement/Defect
- ✅ Updated "How the Agent Works" example — Changed from "What risk factors does Apple face?" to "What requirements does the high-voltage battery have?" with manufacturing schema flow
- ✅ Updated sample queries — Replaced financial queries (BlackRock, Apple, Microsoft, SEC filings) with manufacturing queries (HVB_3900, R2D2, Electric Powertrain, defects)
- ✅ Updated MCP code example — Changed `MATCH (c:Company)` to `MATCH (c:Component)`

#### MCP Agent notebook (neo4j_langgraph_mcp_agent.ipynb) ✅

1. ✅ **"Your Queries" section** — Replaced SEC filings suggestions with manufacturing queries (HVB_3900 requirements, defects, technology domains, Electric Powertrain components, battery-related changes)
2. **System prompt** — Kept generic (already domain-independent — references "Neo4j database" not specific domain)
3. **Demo queries** — Kept generic (schema inspection, node counts, relationship types)

#### Strands MCP Agent notebook (neo4j_strands_mcp_agent.ipynb) ✅

1. ✅ **"Your Query" section** — Same manufacturing query suggestions as LangGraph notebook

#### Aura Agents API notebook (aura_agent_client.ipynb) ✅

1. ✅ **Intro text** — Changed "SEC 10-K filings" to "manufacturing product development data"
2. ✅ **All query examples** — Replaced financial queries with manufacturing:
   - "Tell me about Apple Inc and their major institutional investors" → "Tell me about the R2D2 product and its technology domains"
   - "What risks do Apple and Microsoft share?" → "What requirements do HVB_3900 and PDU_1500 have in common?"
   - "What do the SEC filings say about AI and machine learning?" → "What do the requirements say about thermal management and cooling?"
   - "Which company has the most risk factors?" → "Which component has the most requirements?"
   - "What products does NVIDIA offer according to their SEC filings?" → "What defects have been found in the Electric Powertrain domain?"
3. ✅ **Async example** — Changed Apple/Microsoft/NVIDIA businesses to Electric Powertrain/Chassis/Body domain queries
4. ✅ **Custom queries** — Changed to battery changes and test cases
5. ✅ **Summary** — Changed "knowledge graph" to "manufacturing knowledge graph"
6. ✅ **Section headers** — "Company Overview" → "Product Overview", "Comparative Analysis" → "Component Analysis"

#### Lab 7 README.md ✅

- ✅ Updated lab overview — "SEC 10-K filings" → "manufacturing product development data"
- ✅ Updated "query company data" → "query component and requirement data"
- ✅ Updated example usage — Apple risk factors → HVB_3900 battery requirements
- ✅ Updated sample questions — All financial queries replaced with manufacturing queries

### Changes Made — Lab 9: Hybrid Search (New Lab)

Created two new notebooks in `Lab_5_GraphRAG/`:

#### 05_fulltext_search.ipynb (new) ✅

1. ✅ **Full-text index creation** — Creates `requirement_text` index on Chunk.text and `search_entities` index on Component/Requirement names and descriptions
2. ✅ **Basic search** — Demonstrates simple term search with manufacturing terms (thermal, coolant)
3. ✅ **Fuzzy matching** — Shows typo tolerance with `battrey~`, `coling~1`, `safty~`
4. ✅ **Wildcard search** — Demonstrates prefix patterns with `therm*`, `volt*`, `monitor*`
5. ✅ **Boolean search** — Shows AND, OR, NOT, and phrase matching with manufacturing terms
6. ✅ **Entity search** — Searches Component and Requirement names via `search_entities` index
7. ✅ **Graph traversal** — Combines fulltext search with traversal to parent Requirement and Component
8. ✅ **Comparison guide** — When to use full-text vs. vector search

#### 06_hybrid_search.ipynb (new) ✅

1. ✅ **HybridRetriever** — Combines `requirement_embeddings` vector index with `requirement_text` fulltext index
2. ✅ **Alpha tuning** — Demonstrates alpha parameter with 0.0 (fulltext only), 0.5 (balanced), 1.0 (vector only)
3. ✅ **HybridCypherRetriever** — Graph-enhanced hybrid retrieval with manufacturing traceability traversal (Component → Requirement → Chunk + adjacent chunks)
4. ✅ **Complete GraphRAG pipeline** — Hybrid retrieval + LLM generation for question answering
5. ✅ **Retriever selection guide** — Summary table of all retriever types and when to use each

### Changes Made — Lab 5 README.md ✅

- ✅ Complete rewrite from 4-notebook to 6-notebook structure
- ✅ Replaced all SEC/financial references with manufacturing domain (products, components, requirements)
- ✅ Updated all code examples to use `requirement_embeddings` index and manufacturing Cypher
- ✅ Added Notebook 5 (Full-Text Search) and Notebook 6 (Hybrid Search) sections
- ✅ Updated Retriever Selection Guide with all retriever types
- ✅ Updated Key Concepts Reference to include full-text index and alpha parameter

---

## Cross-Cutting Concerns

These items affect multiple phases and should be addressed throughout:

1. ⬜ **CLAUDE.md** — Update the project instructions file to reflect the new schema, node types, relationships, and lab structure once all changes are complete.
2. ⬜ **Lab cross-references** — Every notebook has "Next:" links at the bottom. These all need updating when labs are renumbered or reorganized.
3. ⬜ **Screenshots and images** — Any screenshots showing the financial graph need to be retaken with the manufacturing graph.
4. ✅ **CONFIG.txt** — No changes needed. The same credential structure works for any Neo4j database.
5. ⬜ **Data preparation prerequisite** — Manufacturing data needs to be loaded into Neo4j Aura with embeddings and indexes before labs can be tested.
