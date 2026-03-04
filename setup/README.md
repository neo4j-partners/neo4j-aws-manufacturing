# Setup — Neo4j Manufacturing Database

Three tools for the manufacturing workshop:

- **populate** — loads the knowledge graph into Neo4j (Lab 1 database)
- **solutions_openai** — LangChain+OpenAI agent that validates Lab 2 Aura Agents
- **solutions_bedrock** — GraphRAG validator that validates Lab 5 (Neo4j + AWS Bedrock)

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Two Neo4j Aura instances** — one for populate/solutions_openai (Labs 1-2), one for solutions_bedrock (Lab 5)
- **OpenAI API key** (for populate and solutions_openai)
- **AWS credentials** with Bedrock access (for solutions_bedrock)

## Quick Start

The full workflow creates the main database, validates Lab 2, then validates Lab 5 on a separate instance.

### Step 1: Populate the Main Database (Lab 1)

Create your first Neo4j Aura instance and load the complete knowledge graph:

```bash
cd setup/populate

# Configure credentials (edit .env or rely on ../../CONFIG.txt)
cp .env.example .env
# Edit .env with your Neo4j URI, username, password, and OpenAI API key

# Load the graph (nodes, relationships, embeddings, and indexes in one step)
uv run populate-manufacturing-db load

# Verify counts
uv run populate-manufacturing-db verify
```

This creates 549 nodes, 1,102 relationships, 96 OpenAI embeddings, and 2 vector indexes (~21s).

### Step 2: Validate Lab 2 (Aura Agents) with OpenAI

Point `solutions_openai` at the same Aura instance from Step 1. This runs the same questions from the Lab 2 Aura Agent walkthrough and validates the tools work correctly:

```bash
cd setup/solutions_openai

# Configure credentials
# Edit .env with NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAI_API_KEY

# Run the full test suite (3 phases: preflight, tool tests, agent integration)
uv run manufacturing-agent test

# Or start an interactive chat session
uv run manufacturing-agent chat
```

The test suite has 3 phases:
1. **Database preflight** — verifies constraints, indexes, node counts, embeddings (no OpenAI calls)
2. **Direct tool tests** — calls each of the 5 tools independently
3. **Agent integration** — routes 6 questions through the LLM to validate tool selection

### Step 3: Validate Lab 5 (GraphRAG) with Bedrock

Create a **second** Neo4j Aura instance for Lab 5. The solutions_bedrock validator creates its own data from scratch (different graph schema with Chunks):

```bash
cd setup/solutions_bedrock

# Configure credentials
# Edit .env with NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, MODEL_ID, EMBEDDING_MODEL_ID, REGION

# Run the full validation suite (6 phases matching Lab 5 notebooks 01-06)
uv sync
uv run graphrag-validator test

# Or start an interactive chat session
uv run graphrag-validator chat
```

## CLI Commands

### populate-manufacturing-db

| Command | Description |
|---|---|
| `load` | Full pipeline: CSV data → nodes → relationships → embeddings → vector indexes |
| `verify` | Print node/relationship counts (read-only) |
| `samples` | Run 9 sample queries including vector similarity and semantic search |
| `test-queries` | Run 8 semantic similarity and hybrid search test queries (requires OpenAI API key) |
| `clean` | Delete all nodes and relationships |

### manufacturing-agent (solutions_openai)

| Command | Description |
|---|---|
| `test` | 3-phase validation: database preflight, direct tool tests, agent integration |
| `chat` | Interactive chat session with the manufacturing agent |

### graphrag-validator (solutions_bedrock)

| Command | Description |
|---|---|
| `test` | Run all 6 phases: data loading, embeddings, vector/cypher/fulltext/hybrid search |
| `chat` | Interactive GraphRAG chat session using HybridCypherRetriever |

## What `load` Does

A single command runs the entire setup pipeline:

1. **Constraints** — 11 uniqueness constraints for all node types
2. **Indexes** — 5 property indexes for common query fields
3. **Nodes** — 549 nodes across 11 labels from CSV files
4. **Relationships** — 1,102 relationships across 12 types (including derived)
5. **Embeddings** — 96 OpenAI embeddings (70 Requirement + 26 Defect descriptions)
6. **Vector indexes** — `requirementEmbeddings` and `defectEmbeddings` (1536 dims, cosine)
7. **Verify** — prints final counts

Total runtime: ~21s (4s load + 17s embedding).

## What `graphrag-validator test` Does

Replicates the full Lab 5 notebook sequence, creating data from scratch on a separate Aura instance:

| Phase | Notebook | What it does |
|---|---|---|
| 1 | 01_data_loading | Clear Lab 5 data, load CSVs, create base graph (Product/TechnologyDomain/Component), split text into chunks, create Requirement + Chunk nodes |
| 2 | 02_embeddings | Generate Titan V2 embeddings for chunks, store on Chunk nodes, create vector index, test raw vector search |
| 3 | 03_vector_retriever | VectorRetriever search + GraphRAG pipeline question |
| 4 | 04_vector_cypher_retriever | VectorCypherRetriever with graph context expansion + GraphRAG |
| 5 | 05_fulltext_search | Create fulltext indexes, test exact/fuzzy/wildcard/boolean/entity search |
| 6 | 06_hybrid_search | HybridRetriever, HybridCypherRetriever, GraphRAG with hybrid |

## Graph Data Model

### Labs 1-2 (populate / solutions_openai)

```
(Product) -[:PRODUCT_HAS_DOMAIN]-> (TechnologyDomain) -[:DOMAIN_HAS_COMPONENT]-> (Component)
(Component) -[:COMPONENT_HAS_REQ]-> (Requirement)
(Requirement) -[:TESTED_WITH]-> (TestSet) -[:CONTAINS_TEST_CASE]-> (TestCase)
(TestCase) -[:DETECTED]-> (Defect)
(Change) -[:CHANGE_AFFECTS_REQ]-> (Requirement)
(Requirement) -[:REQUIRES_ML]-> (Milestone) -[:NEXT]-> (Milestone)
(TestCase) -[:REQUIRES_ML]-> (MaturityLevel)
(TestCase) -[:REQUIRES]-> (Resource)
```

**11 node labels** — Product, TechnologyDomain, Component, Requirement, TestSet, TestCase, Defect, Change, Milestone, MaturityLevel, Resource

### Lab 5 (solutions_bedrock)

```
(Product) -[:PRODUCT_HAS_DOMAIN]-> (TechnologyDomain) -[:DOMAIN_HAS_COMPONENT]-> (Component)
(Component) -[:COMPONENT_HAS_REQ]-> (Requirement) -[:HAS_CHUNK]-> (Chunk) -[:NEXT_CHUNK]-> (Chunk)
```

**Vector index**: `requirement_embeddings` on Chunk.embedding (1024 dims, Titan V2)
**Fulltext indexes**: `requirement_text` (Chunk.text), `search_entities` (Component/Requirement names)

## Solutions Agent — Lab 2 Recreation

The `solutions_openai/` agent recreates the Lab 2 Aura Agent using LangChain, LangGraph, and OpenAI. It implements all 5 tools:

| Tool | Type | Description |
|---|---|---|
| `get_component_overview` | Cypher Template | Component info with requirements and defects |
| `get_test_coverage` | Cypher Template | Test coverage status per requirement |
| `get_milestone_readiness` | Cypher Template | Open tests, defects, and effort for a milestone |
| `search_requirement_content` | Vector Search | Semantic search over requirement descriptions |
| `query_database` | Text2Cypher | Natural language → Cypher translation |

## Project Structure

```
setup/
├── populate/                          # Database loader (Labs 1-2)
│   ├── pyproject.toml
│   ├── .env.example
│   └── src/populate_manufacturing_db/
│       ├── main.py          # Typer CLI: load, clean, verify, samples, test-queries
│       ├── config.py        # pydantic-settings (.env / CONFIG.txt fallback)
│       ├── schema.py        # Constraints, property indexes, vector indexes
│       ├── loader.py        # CSV reading, batched MERGE, derived nodes/rels
│       ├── embedder.py      # OpenAI embeddings (text-embedding-ada-002)
│       ├── formatting.py    # Shared display helpers (header, cypher, val, table, banner)
│       ├── samples.py       # 9 sample queries showcasing the graph
│       └── test_queries.py  # 8 semantic similarity + hybrid search queries
├── solutions_openai/                  # LangChain + OpenAI agent (Lab 2 validation)
│   ├── pyproject.toml
│   └── src/manufacturing_agent/
│       ├── config.py        # pydantic-settings (.env)
│       ├── agent.py         # 5 tools + LangGraph ReAct agent
│       └── main.py          # Typer CLI: test (3 phases), chat
└── solutions_bedrock/                 # Lab 5 GraphRAG validator (Neo4j + Bedrock)
    ├── pyproject.toml
    └── src/graphrag_validator/
        ├── config.py        # pydantic-settings (.env)
        ├── data.py          # Data loading, graph creation, embeddings, indexes
        ├── retrievers.py    # Schema constants + 4 retriever builders
        └── main.py          # Typer CLI: test (6 phases), chat
```

## Data Source

CSV files in `TransformedData/` at the repository root. The dataset covers an automotive R2D2 product with Electric Powertrain, Chassis, Body, and Infotainment technology domains.

## Configuration

- **populate** looks for `.env` in `setup/populate/` first, then falls back to `CONFIG.txt` at the repository root. See `.env.example` for all available settings.
- **solutions_openai** reads from `.env` in `setup/solutions_openai/`. Required variables: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`.
- **solutions_bedrock** reads from `.env` in `setup/solutions_bedrock/`. Required variables: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `MODEL_ID`, `EMBEDDING_MODEL_ID`, `REGION`.
