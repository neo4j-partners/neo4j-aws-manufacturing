# Setup — Neo4j Manufacturing Database

Two tools for the manufacturing workshop: **populate** loads the knowledge graph into Neo4j, and **solutions** runs a LangChain+OpenAI agent that recreates the Lab 2 Aura Agent in code.

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Neo4j Aura** instance (or any Neo4j 5.x+ database)
- **OpenAI API key** (used for embeddings and the LangChain agent)

## Quick Start — Populate

```bash
cd setup/populate

# Configure credentials (edit .env or rely on ../../CONFIG.txt)
cp .env.example .env
# Edit .env with your Neo4j URI, username, password, and OpenAI API key

# Load the graph (nodes, relationships, embeddings, and indexes in one step)
uv run populate-manufacturing-db load

# Verify counts
uv run populate-manufacturing-db verify

# Run sample queries (includes vector similarity search)
uv run populate-manufacturing-db samples

# Run semantic similarity and hybrid search test queries
uv run populate-manufacturing-db test-queries
```

## Quick Start — Solutions (LangChain Agent)

```bash
cd setup/solutions

# Configure credentials
# Edit .env with NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, OPENAI_API_KEY

# Run the full test suite (9 Lab 2 sample questions)
uv run manufacturing-agent test

# Or start an interactive chat session
uv run manufacturing-agent chat
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

### manufacturing-agent

| Command | Description |
|---|---|
| `test` | Run all 9 Lab 2 sample questions as a test suite with pass/fail and timing |
| `chat` | Interactive chat session with the manufacturing agent |

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

## Graph Data Model

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

## Project Structure

```
setup/
├── populate/                          # Database loader
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
└── solutions/                         # LangChain + OpenAI agent (Lab 2 recreation)
    ├── pyproject.toml
    └── src/manufacturing_agent/
        ├── config.py        # pydantic-settings (.env)
        ├── agent.py         # 5 tools + LangGraph ReAct agent
        └── main.py          # Typer CLI: test, chat
```

## Solutions Agent — Lab 2 Recreation

The `solutions/` agent recreates the Lab 2 Aura Agent using LangChain, LangGraph, and OpenAI. It implements all 5 tools:

| Tool | Type | Description |
|---|---|---|
| `get_component_overview` | Cypher Template | Component info with requirements and defects |
| `get_test_coverage` | Cypher Template | Test coverage status per requirement |
| `get_milestone_readiness` | Cypher Template | Open tests, defects, and effort for a milestone |
| `search_requirement_content` | Vector Search | Semantic search over requirement descriptions |
| `query_database` | Text2Cypher | Natural language → Cypher translation |

## Data Source

CSV files in `TransformedData/` at the repository root. The dataset covers an automotive R2D2 product with Electric Powertrain, Chassis, Body, and Infotainment technology domains.

## Configuration

- **populate** looks for `.env` in `setup/populate/` first, then falls back to `CONFIG.txt` at the repository root. See `.env.example` for all available settings.
- **solutions** reads from `.env` in `setup/solutions/`. Required variables: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`.
