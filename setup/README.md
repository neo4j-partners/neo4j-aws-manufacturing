# Setup — Neo4j Manufacturing Database

Populates a Neo4j Aura instance with the Manufacturing Product Development dataset and generates vector embeddings for semantic search.

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Neo4j Aura** instance (or any Neo4j 5.x+ database)
- **OpenAI API key** (used during embedding phase of load and semantic search samples)

## Quick Start

```bash
cd setup/populate

# Install dependencies
uv sync

# Configure credentials (edit .env or rely on ../../CONFIG.txt)
cp .env.example .env
# Edit .env with your Neo4j URI, username, and password

# Load the graph (nodes, relationships, embeddings, and indexes in one step)
uv run populate-manufacturing-db load

# Verify counts
uv run populate-manufacturing-db verify

# Run sample queries (includes vector similarity search)
uv run populate-manufacturing-db samples

# Run semantic similarity and hybrid search test queries
uv run populate-manufacturing-db test-queries
```

## CLI Commands

| Command | Description |
|---|---|
| `load` | Full pipeline: CSV data → nodes → relationships → embeddings → vector indexes |
| `verify` | Print node/relationship counts (read-only) |
| `samples` | Run 9 sample queries including vector similarity and semantic search |
| `test-queries` | Run 8 semantic similarity and hybrid search test queries (requires OpenAI API key) |
| `clean` | Delete all nodes and relationships |

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
setup/populate/
├── pyproject.toml
├── .env.example
├── PROPOSAL.md
└── src/populate_manufacturing_db/
    ├── main.py          # Typer CLI: load, clean, verify, samples, test-queries
    ├── config.py        # pydantic-settings (.env / CONFIG.txt fallback)
    ├── schema.py        # Constraints, property indexes, vector indexes
    ├── loader.py        # CSV reading, batched MERGE, derived nodes/rels
    ├── embedder.py      # OpenAI embeddings (embed_text, embed_descriptions)
    ├── formatting.py    # Shared display helpers (header, cypher, val, table, banner)
    ├── samples.py       # 9 sample queries showcasing the graph
    └── test_queries.py  # 8 semantic similarity + hybrid search queries
```

## Data Source

CSV files in `TransformedData/` at the repository root. The dataset covers an automotive R2D2 product with Electric Powertrain, Chassis, Body, and Infotainment technology domains.

## Configuration

The tool looks for `.env` in the `setup/populate/` directory first, then falls back to `CONFIG.txt` at the repository root. See `.env.example` for all available settings.
