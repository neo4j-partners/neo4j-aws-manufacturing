# Proposal: Neo4j Manufacturing Data Population Tool

## Implementation Status

| Step | Status | Notes |
|---|---|---|
| `pyproject.toml` | DONE | uv sync successful, 25 packages installed |
| `.env.example` | DONE | Neo4j + Bedrock config template |
| `config.py` | DONE | pydantic-settings with .env / CONFIG.txt fallback |
| `schema.py` | DONE | 11 constraints, 5 indexes, 2 vector indexes |
| `loader.py` | DONE | 9 node types + 2 derived, 9 rel types + 3 derived, CSV whitespace stripping, latin-1 fallback |
| `embedder.py` | DONE | boto3 Bedrock Titan Embed v2, batch-25, skip-if-already-embedded |
| `samples.py` | DONE | 8 sample queries including 2 vector similarity searches |
| `main.py` | DONE | 5 CLI commands: load, embed, clean, verify, samples |
| `uv sync` | DONE | Python 3.13, lockfile generated, all imports verified |
| **End-to-end test** | DONE | 549 nodes, 1,102 relationships, 96 embeddings in ~21s total |

### Test Results

```
load:   549 nodes (11 labels), 1,102 relationships — 4s
embed:  96 embeddings (70 Requirement + 26 Defect) — 17s
verify: All counts match expected
samples: All 8 queries return results, vector search working
clean:  549 nodes deleted
```

### Bugs Fixed During Testing

1. **CSV encoding**: `requirements.csv` uses latin-1 encoding (German umlauts). Added utf-8 → latin-1 fallback in `read_csv()`.
2. **Milestone NEXT ordering**: Deadline strings (`M/D/YY`) don't sort correctly as strings. Changed to sort by `milestone_id` which is already chronological.

## Overview

Create a Python CLI tool (`populate-manufacturing-db`) that reads the CSV files in `TransformedData/` and populates a Neo4j database with the manufacturing product development graph. The tool follows the same architecture and uv best practices as the `populate_aircraft_db` reference project.

## Reference

Based on the patterns in `/Users/ryanknight/projects/aws-databricks-neo4j-lab/lab_setup/populate_aircraft_db`, which uses:
- **uv** for package management with a `pyproject.toml` and lockfile
- **Typer** for CLI commands with **Rich** for terminal output
- **pydantic-settings** for `.env`-based configuration
- **neo4j** Python driver with batched `MERGE` queries
- A clear separation: `config.py`, `schema.py`, `loader.py`, `main.py`, `samples.py`

## Graph Data Model (from PDF)

The data model diagram defines these nodes and relationships:

### Nodes (8 types, from 8 CSV files)

| Node Label | Source CSV | ID Property | Other Properties |
|---|---|---|---|
| **Product** | `products.csv` | `product_id` | `name`, `description` |
| **TechnologyDomain** | `technology_domains.csv` | `technology_domain_id` | `name` |
| **Component** | `components.csv` | `component_id` | `name`, `description` |
| **Requirement** | `requirements.csv` | `requirement_id` | `name`, `description`, `name_de`, `description_de`, `vehicle_project`, `technology_cluster`, `component`, `type`, `embedding` |
| **TestSet** | `test_sets.csv` | `test_set_id` | `name` |
| **TestCase** | `test_cases.csv` | `test_case_id` | `name`, `status`, `resources`, `duration_hours`, `start_date`, `end_date`, `responsibility`, `i_stage` |
| **Defect** | `defects.csv` | `defect_id` | `description`, `severity`, `priority`, `assigned_to`, `status`, `creation_date`, `resolved_date`, `resolution`, `comments`, `embedding` |
| **Change** | `changes.csv` | `change_proposal_id` | `description`, `criticality`, `dev_cost_usd`, `production_cost_usd_per_unit`, `status`, `urgency`, `risk` |
| **Milestone** | `milestones.csv` | `milestone_id` | `deadline` |

### Relationships (9 types, from 9 CSV files + data model)

| Relationship | Source CSV | From → To |
|---|---|---|
| **PRODUCT_HAS_DOMAIN** | `product_technology_domains.csv` | Product → TechnologyDomain |
| **DOMAIN_HAS_COMPONENT** | `technology_domains_components.csv` | TechnologyDomain → Component |
| **COMPONENT_HAS_REQ** | `components_requirements.csv` | Component → Requirement |
| **TESTED_WITH** | `requirements_test_sets.csv` | Requirement → TestSet |
| **CONTAINS_TEST_CASE** | `test_sets_test_cases.csv` | TestSet → TestCase |
| **DETECTED** | `test_case_defect.csv` | TestCase → Defect |
| **CHANGE_AFFECTS_REQ** | `changes_requirements.csv` | Change → Requirement |
| **REQUIRES_ML** | `requirements_test_sets_milestone.csv` | Requirement → Milestone (via test_set context) |
| **REQUIRES_FLAWLESS_TEST_SET** | `requirements_test_sets_milestone.csv` | Requirement → TestSet (with milestone context) |

**Note on `requirements_test_sets_milestone.csv`:** This is a three-way join table (`requirement_id`, `test_set_id`, `milestone_id`). Per the data model diagram, this creates:
- `(Requirement)-[:REQUIRES_ML]->(Milestone)` — the milestone by which a requirement must be met
- `(Requirement)-[:REQUIRES_FLAWLESS_TEST_SET]->(TestSet)` — which test set must pass flawlessly, with the `milestone_id` stored as a relationship property

The `ML_FOR_REQ` relationship on the diagram connects Milestone back to Requirement (same data, reverse traversal — we create the forward direction only and rely on Cypher's bidirectional matching).

**Additional relationship from the data model:**
- **NEXT** between Milestones — derived by sorting milestones by deadline and creating a linked list chain (similar to the `NEXT_CHUNK` pattern in the reference project)

### Node Not in CSV (Derived)

| Node Label | Source | Notes |
|---|---|---|
| **MaturityLevel** | Derived from `test_cases.csv` `I-Stage` column | Unique I-Stage values (e.g., `I-300`, `I-400`) become MaturityLevel nodes. TestCases link to them via `REQUIRES_ML`. |
| **Resource** | Derived from `test_cases.csv` `Resources` column | Unique resource strings (e.g., `Test lab measuring instruments`) become Resource nodes. TestCases link to them via `REQUIRES`. |

## Project Structure

```
setup/populate/
├── PROPOSAL.md                          # This file
├── pyproject.toml                       # uv package definition
├── uv.lock                             # Locked dependencies (generated)
├── .env.example                         # Configuration template
├── .venv/                              # Virtual environment (generated)
├── src/populate_manufacturing_db/
│   ├── __init__.py
│   ├── config.py                        # Settings via pydantic-settings
│   ├── main.py                          # Typer CLI: load, embed, clean, verify, samples
│   ├── embedder.py                      # Bedrock Titan embedding + vector index creation
│   ├── schema.py                        # Constraints, indexes, vector indexes
│   ├── loader.py                        # CSV reading, batched MERGE queries
│   └── samples.py                       # 8 exploratory read-only queries
```

## Configuration (`.env`)

```env
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
REGION=us-west-2
```

The existing `CONFIG.txt` at the repo root already has these values, so `config.py` will look for `.env` in the populate directory first, then fall back to `../../CONFIG.txt`. The embedding config is needed for the `embed` command (see below).

## CLI Commands

### `uv run populate-manufacturing-db load`

1. Connect to Neo4j and verify connectivity
2. Create uniqueness constraints for all 8+ node types
3. Create property indexes for common query fields
4. Load nodes from CSV files (batched, 1000 rows per batch, using `MERGE`)
5. Load relationships from CSV files (batched, using `MATCH` + `MERGE`)
6. Create the `NEXT` chain between Milestones (sorted by deadline)
7. Print verification counts

### `uv run populate-manufacturing-db embed`

1. Connect to Neo4j and verify connectivity
2. Call AWS Bedrock Titan Embed (`amazon.titan-embed-text-v2:0`) to generate embeddings for:
   - **Requirement** `description` field (70 rows, avg 188 chars, max 400 chars — well within token limits)
   - **Defect** `description` field (26 rows, avg 50 chars, max 67 chars)
3. Store embeddings directly on the existing nodes as an `embedding` property (no chunking needed — descriptions are short enough to embed whole)
4. Create two vector indexes for similarity search:
   - `requirementEmbeddings` on `Requirement.embedding` (cosine similarity, 1024 dims for Titan v2)
   - `defectEmbeddings` on `Defect.embedding` (cosine similarity, 1024 dims for Titan v2)
5. Print summary (count of nodes embedded, index status)

**Why no chunking:** Requirement descriptions max out at 400 characters (~60-80 tokens). Defect descriptions max out at 67 characters (~10-15 tokens). Both are far below the Titan Embed v2 input limit (8,192 tokens). Embedding whole descriptions preserves full semantic meaning without the lossy overhead of splitting and reassembling.

**Batching for Bedrock:** Embeddings are generated in batches (e.g., 25 at a time) to respect Bedrock rate limits, with each batch written back to Neo4j via:

```cypher
UNWIND $batch AS row
MATCH (r:Requirement {requirement_id: row.id})
SET r.embedding = row.embedding
```

### `uv run populate-manufacturing-db clean`

Batched deletion of all nodes and relationships (500 at a time in a loop until empty).

### `uv run populate-manufacturing-db verify`

Read-only command that prints node counts per label and relationship counts per type.

### `uv run populate-manufacturing-db samples`

Run a set of exploratory queries demonstrating the graph, such as:
1. **Product overview** — Product → TechnologyDomains → Components tree
2. **Requirement traceability** — Requirement → TestSets → TestCases → Defects chain
3. **Change impact analysis** — Change → affected Requirements → their TestSets
4. **Milestone timeline** — Milestones in order with linked requirements and their test readiness
5. **Defect summary** — Open defects with severity, linked back through TestCase → TestSet → Requirement → Component
6. **Test coverage** — Requirements with/without test sets, test cases with pass/fail status
7. **Semantic search: Requirements** — Vector similarity search over Requirement embeddings (e.g., find requirements related to "thermal management")
8. **Semantic search: Defects** — Vector similarity search over Defect embeddings (e.g., find defects related to "battery temperature")

## Dependencies (`pyproject.toml`)

```toml
[project]
name = "populate-manufacturing-db"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "neo4j>=5.17.0",
    "boto3>=1.35.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.0.0",
    "typer>=0.15.0",
    "rich>=13.0.0",
]

[project.scripts]
populate-manufacturing-db = "populate_manufacturing_db.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Note:** `boto3` is used directly for Bedrock Titan embeddings (no LangChain wrapper needed for a simple embed call). This keeps the dependency footprint minimal.

## Key Implementation Details

### Batched MERGE Pattern (same as reference)

All node and relationship creation uses batched `MERGE` for idempotency:

```python
# Nodes — example for Requirement
UNWIND $batch AS row
MERGE (r:Requirement {requirement_id: row['requirement_id']})
SET r.name = row['Requirement'],
    r.description = row['Description'],
    r.name_de = row['Anforderung'],
    r.description_de = row['Beschreibung'],
    r.vehicle_project = row['Vehicle Project'],
    r.technology_cluster = row['Technology Cluster'],
    r.component = row['Component'],
    r.type = row['Type']

# Relationships — example for TESTED_WITH
UNWIND $batch AS row
MATCH (r:Requirement {requirement_id: row['requirement_id']})
MATCH (ts:TestSet {test_set_id: row['test_set_id']})
MERGE (r)-[:TESTED_WITH]->(ts)
```

### Milestone NEXT Chain

After loading milestones, sort by deadline and create a linked list:

```cypher
MATCH (m:Milestone)
WITH m ORDER BY m.deadline
WITH collect(m) AS milestones
UNWIND range(0, size(milestones)-2) AS i
WITH milestones[i] AS current, milestones[i+1] AS next
MERGE (current)-[:NEXT]->(next)
```

### CSV Path Resolution

The `config.py` module will resolve the data directory to `TransformedData/` relative to the repository root (two levels up from the package), matching how the reference project resolves its data path.

### Error Handling

- Neo4j connection: catch `ServiceUnavailable` / `OSError`, print helpful message, exit
- CSV reading: standard `csv.DictReader`, fail fast on missing files
- Batched deletion: retry loop until count reaches 0

## Embedding Implementation Details

### Why Whole-Description Embedding (No Chunking)

We analyzed the actual data to determine whether chunking is needed:

| Field | Rows | Avg Length | Max Length | Titan v2 Limit |
|---|---|---|---|---|
| Requirement `description` | 70 | 188 chars | 400 chars | ~32,000 chars |
| Defect `description` | 26 | 50 chars | 67 chars | ~32,000 chars |

All descriptions are far below the model's input limit. Embedding whole descriptions:
- **Preserves full semantic meaning** — no information lost to chunk boundaries
- **Simpler implementation** — no splitter, no Chunk nodes, no NEXT_CHUNK chains
- **Fewer API calls** — 96 total embeddings vs. potentially hundreds of chunks
- **Cleaner graph** — embeddings live directly on the domain nodes (Requirement, Defect) rather than on intermediary Chunk nodes, so vector search results are immediately actionable without an extra traversal hop

### Bedrock Titan Embed v2 Integration

```python
# embedder.py — direct boto3 call, no LangChain wrapper needed
import boto3, json

bedrock = boto3.client("bedrock-runtime", region_name=settings.region)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using Titan Embed v2."""
    embeddings = []
    for text in texts:
        response = bedrock.invoke_model(
            modelId=settings.embedding_model_id,
            body=json.dumps({
                "inputText": text,
                "dimensions": 1024,
                "normalize": True,
            }),
        )
        result = json.loads(response["body"].read())
        embeddings.append(result["embedding"])
    return embeddings
```

### Vector Index Creation

```cypher
-- Requirement embeddings (1024 dims, cosine similarity)
CREATE VECTOR INDEX requirementEmbeddings IF NOT EXISTS
FOR (r:Requirement) ON (r.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}}

-- Defect embeddings (1024 dims, cosine similarity)
CREATE VECTOR INDEX defectEmbeddings IF NOT EXISTS
FOR (d:Defect) ON (d.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}}
```

### Sample Vector Search Query

```cypher
-- Find requirements semantically similar to a query
CALL db.index.vector.queryNodes('requirementEmbeddings', 5, $queryEmbedding)
YIELD node AS req, score
RETURN req.requirement_id, req.name, req.description, score
ORDER BY score DESC
```

## What This Tool Does NOT Include

- **No LLM entity extraction** — the manufacturing data is fully structured in CSVs, no unstructured text to process with an LLM pipeline
- **No chunking** — descriptions are short enough to embed whole (max 400 chars)
- **No fulltext indexes** — can be added in a future iteration if workshop labs need them

## Usage Workflow

```bash
cd setup/populate
cp .env.example .env
# Edit .env with Neo4j credentials (or it will read from ../../CONFIG.txt)

uv sync
uv run populate-manufacturing-db load      # Load all CSV data as nodes + relationships
uv run populate-manufacturing-db embed     # Generate embeddings for Requirements + Defects
uv run populate-manufacturing-db verify    # Check counts
uv run populate-manufacturing-db samples   # Explore the graph (includes vector search)
uv run populate-manufacturing-db clean     # Start over if needed
```
