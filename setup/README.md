# Setup — Neo4j Manufacturing Database

Populates a Neo4j Aura instance with the Manufacturing Product Development dataset and generates vector embeddings for semantic search.

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Neo4j Aura** instance (or any Neo4j 5.x+ database)
- **AWS credentials** configured for Bedrock access (embedding commands only)

## Quick Start

```bash
cd setup/populate

# Install dependencies
uv sync

# Configure credentials (edit .env or rely on ../../CONFIG.txt)
cp .env.example .env
# Edit .env with your Neo4j URI, username, and password

# Load the graph
uv run populate-manufacturing-db load

# Generate embeddings (requires AWS Bedrock access)
uv run populate-manufacturing-db embed

# Verify counts
uv run populate-manufacturing-db verify
```

## CLI Commands

| Command | Description |
|---|---|
| `load` | Load all CSV data as nodes + relationships (549 nodes, 1,102 rels) |
| `embed` | Generate Titan v2 embeddings for Requirement and Defect descriptions |
| `verify` | Print node/relationship counts (read-only) |
| `samples` | Run 8 sample queries including vector similarity search |
| `test-queries` | Run semantic similarity and hybrid search test queries |
| `clean` | Delete all nodes and relationships |

## Graph Data Model

```
(Product) -[:PRODUCT_HAS_DOMAIN]-> (TechnologyDomain) -[:DOMAIN_HAS_COMPONENT]-> (Component)
(Component) -[:COMPONENT_HAS_REQ]-> (Requirement)
(Requirement) -[:TESTED_WITH]-> (TestSet) -[:CONTAINS_TEST_CASE]-> (TestCase)
(TestCase) -[:DETECTED]-> (Defect)
(Change) -[:CHANGE_AFFECTS_REQ]-> (Requirement)
(Requirement) -[:REQUIRES_ML]-> (Milestone) -[:NEXT]-> (Milestone)
```

**11 node labels** — Product, TechnologyDomain, Component, Requirement, TestSet, TestCase, Defect, Change, Milestone, MaturityLevel, Resource

**Vector indexes** — `requirementEmbeddings` and `defectEmbeddings` (1024 dims, cosine similarity)

## Data Source

CSV files in `TransformedData/` at the repository root. The dataset covers an automotive R2D2 product with Electric Powertrain, Chassis, Body, and Infotainment technology domains.

## Configuration

The tool looks for `.env` in the `setup/populate/` directory first, then falls back to `CONFIG.txt` at the repository root. See `.env.example` for all available settings.
