# Lab 5 - GraphRAG with Neo4j

This lab teaches you how to build Graph Retrieval-Augmented Generation (GraphRAG) applications using the official **neo4j-graphrag** Python library. Through six hands-on notebooks, you'll progress from understanding graph structure to building production-ready GraphRAG pipelines with hybrid search.


## Before You Begin

> [!IMPORTANT]
> Complete these steps before running the notebooks.

**Prerequisites:**
- Lab 1 completed (Neo4j Aura database running)
- Lab 4 completed (SageMaker with repository cloned)

**Configure Neo4j Connection:**

Open `CONFIG.txt` in the root folder of your SageMaker JupyterLab environment and add your Neo4j credentials from Lab 1:

```ini
# Neo4j Aura (add your credentials from Lab 1)
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
```

> [!NOTE]
> Only the Neo4j settings need to be configured. The AWS Bedrock settings (MODEL_ID, EMBEDDING_MODEL_ID, REGION) are already set to working defaults.


## What is GraphRAG?

GraphRAG combines the semantic understanding of vector search with the structural relationships in knowledge graphs. Unlike traditional RAG that treats documents as isolated chunks, GraphRAG leverages graph connections to provide richer context to LLMs.

**Traditional RAG:**
```
Question → Embed → Vector Search → Top-K Chunks → LLM → Answer
```

**GraphRAG:**
```
Question → Embed → Vector Search → Top-K Nodes → Graph Traversal → Enriched Context → LLM → Answer
```

The graph structure allows you to:
- Follow relationships to find related information
- Understand entity connections (products, components, requirements)
- Retrieve contextual information not present in the original text

## The neo4j-graphrag Library

The `neo4j-graphrag` package is Neo4j's official Python library for building GraphRAG applications. It provides:

| Component | Purpose |
|-----------|---------|
| **Retrievers** | Fetch relevant information from Neo4j (Vector, VectorCypher, Hybrid, Text2Cypher) |
| **Embedders** | Generate vector embeddings from text (Bedrock, OpenAI, etc.) |
| **LLM Interfaces** | Connect to language models (Bedrock, OpenAI, etc.) |
| **GraphRAG** | Orchestrate retriever + LLM into a complete RAG pipeline |

---

## Notebook 1: Understanding Graph Structure for RAG

Before diving into embeddings and retrieval, it's essential to understand how manufacturing data should be structured in a graph database for effective RAG.

### The Manufacturing Traceability Graph

In GraphRAG for manufacturing, we build a traceability graph that connects products to their components, requirements, and text chunks:

1. **Load structured data from CSVs** - Products, TechnologyDomains, and Components
2. **Create traceability relationships** - PRODUCT_HAS_DOMAIN, DOMAIN_HAS_COMPONENT, COMPONENT_HAS_REQ
3. **Split requirement text into chunks** - Linked via `HAS_CHUNK` and `NEXT_CHUNK` relationships

```
(Product) -[:PRODUCT_HAS_DOMAIN]-> (TechnologyDomain) -[:DOMAIN_HAS_COMPONENT]-> (Component)
    (Component) -[:COMPONENT_HAS_REQ]-> (Requirement) -[:HAS_CHUNK]-> (Chunk) -[:NEXT_CHUNK]-> (Chunk)
```

### Why Graph Structure Matters

This structure enables powerful retrieval patterns:
- **Traceability**: When you find a relevant chunk, traverse to its requirement, component, and product
- **Impact analysis**: When a change is proposed, trace which requirements and tests are affected
- **Multi-hop traversal**: Follow relationships to find related entities across the manufacturing chain

### Run the Notebook

**To learn these concepts hands-on, run [`01_data_loading.ipynb`](01_data_loading.ipynb)**

In this notebook, you will:
- Load manufacturing data from CSV files (products, technology domains, components)
- Create Product, TechnologyDomain, and Component nodes using Cypher
- Create PRODUCT_HAS_DOMAIN and DOMAIN_HAS_COMPONENT relationships
- Split requirement description text into chunks with `FixedSizeSplitter`
- Create Requirement and Chunk nodes linked by HAS_CHUNK and NEXT_CHUNK relationships
- Query the graph to verify the traceability chain

**Expected outcome:** A manufacturing traceability graph structure ready for embeddings.

---

## Notebook 2: Creating Embeddings and Vector Indexes

With the graph structure in place, the next step is to enable semantic search by adding vector embeddings to your chunks.

### What Are Embeddings?

Embeddings are numerical representations (vectors) that capture the semantic meaning of text. The key insight is that **similar texts have similar embeddings**, enabling "meaning-based" search rather than just keyword matching.

```python
# These two sentences have very similar embeddings despite different words:
"thermal management system cooling"       → [0.12, -0.45, 0.78, ...]  # 1024 dimensions
"the cooling system must provide heat transfer" → [0.11, -0.44, 0.77, ...]  # Similar vector!
```

This is powerful because a search for "battery cooling requirements" will find content about "thermal management system" even though those exact words don't appear in the query.

### The neo4j-graphrag Embeddings API

The library provides embedders for various providers:

```python
# AWS Bedrock (used in this lab)
from neo4j_graphrag.embeddings import BedrockEmbeddings

embedder = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0")

# Generate an embedding
vector = embedder.embed_query("What are the thermal management requirements?")
# Returns: list[float] with 1024 dimensions
```

### Creating Vector Indexes in Neo4j

Neo4j stores embeddings as node properties and uses vector indexes for fast similarity search:

```cypher
CREATE VECTOR INDEX requirement_embeddings IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {indexConfig: {
  `vector.dimensions`: 1024,
  `vector.similarity_function`: 'cosine'
}}
```

> [!IMPORTANT]
> The `vector.dimensions` must match your embedding model output. Amazon Titan Text Embeddings V2 produces 1024-dimensional vectors.

### Run the Notebook

**To implement embeddings, run [`02_embeddings.ipynb`](02_embeddings.ipynb)**

In this notebook, you will:
- Load manufacturing requirement description text
- Use `FixedSizeSplitter` to chunk text (400 chars with 50 char overlap for demo)
- Generate embeddings for each chunk using Amazon Titan via `BedrockEmbeddings`
- Store embeddings as the `embedding` property on Chunk nodes
- Create a vector index named `requirement_embeddings`
- Perform raw vector searches using `db.index.vector.queryNodes()`
- Compare different queries to see how semantic search finds relevant content

**Expected outcome:** Chunk nodes with embeddings and a working vector index that returns semantically similar results.

---

## Notebook 3: Building Your First GraphRAG Pipeline

With embeddings in place, you can now build a complete question-answering system using the `VectorRetriever` and `GraphRAG` classes.

### VectorRetriever

The `VectorRetriever` abstracts away the complexity of vector search:

```python
from neo4j_graphrag.retrievers import VectorRetriever

retriever = VectorRetriever(
    driver=driver,
    index_name="requirement_embeddings",
    embedder=embedder,
    return_properties=["text"]
)

results = retriever.search(query_text="What are the thermal management requirements?", top_k=5)
```

### The GraphRAG Class

The `GraphRAG` class orchestrates the complete RAG pipeline - retrieval followed by LLM generation:

```python
from neo4j_graphrag.generation import GraphRAG

rag = GraphRAG(retriever=retriever, llm=llm)

response = rag.search(
    query_text="What are the cooling requirements for the battery?",
    retriever_config={"top_k": 5},
    return_context=True
)

print(response.answer)
```

### Run the Notebook

**To build your first pipeline, run [`03_vector_retriever.ipynb`](03_vector_retriever.ipynb)**

In this notebook, you will:
- Initialize a `VectorRetriever` with the `requirement_embeddings` index
- Run diagnostic searches to inspect retrieval results and scores
- Build a complete `GraphRAG` pipeline combining retrieval and generation
- Ask questions about manufacturing requirements and receive grounded answers
- Experiment with different queries about thermal management, energy density, and safety

**Expected outcome:** A working GraphRAG pipeline that answers questions using your manufacturing requirement data.

---

## Notebook 4: Graph-Enhanced Retrieval

The real power of GraphRAG comes from combining vector search with graph traversal. The `VectorCypherRetriever` lets you enrich retrieved chunks with additional context from the manufacturing traceability graph.

### VectorCypherRetriever

This retriever adds a custom Cypher query that runs after vector search, allowing you to traverse relationships:

```python
from neo4j_graphrag.retrievers import VectorCypherRetriever

retrieval_query = """
MATCH (node)<-[:HAS_CHUNK]-(req:Requirement)
OPTIONAL MATCH (comp:Component)-[:COMPONENT_HAS_REQ]->(req)
OPTIONAL MATCH (prev:Chunk)-[:NEXT_CHUNK]->(node)
OPTIONAL MATCH (node)-[:NEXT_CHUNK]->(next:Chunk)
RETURN
    node.text AS context,
    req.name AS requirement,
    comp.name AS component,
    prev.text AS previous_chunk,
    next.text AS next_chunk
"""

retriever = VectorCypherRetriever(
    driver=driver,
    index_name="requirement_embeddings",
    retrieval_query=retrieval_query,
    embedder=embedder
)
```

The `node` variable in the retrieval query refers to each chunk returned by the vector search. You can traverse to the parent Requirement, the Component, and adjacent chunks.

### Why This Matters

Consider a question like "What are the cooling requirements for the battery?" The most relevant chunk might contain the thermal specifications, but the surrounding chunks contain related context. By including graph traversal, you get:

- **Component context**: Which component (e.g., HVB_3900 — High-Voltage Battery) the requirement belongs to
- **Requirement metadata**: The requirement name and description
- **Adjacent chunks**: Previous and next chunks for expanded context

This expanded context often produces significantly better answers because the LLM has more information to work with.

### Run the Notebook

**To implement graph-enhanced retrieval, run [`04_vector_cypher_retriever.ipynb`](04_vector_cypher_retriever.ipynb)**

In this notebook, you will:
- Write custom Cypher retrieval queries that traverse the manufacturing traceability chain
- Configure `VectorCypherRetriever` with requirement and component context
- Implement the expanded context window pattern
- Compare answers from standard `VectorRetriever` vs `VectorCypherRetriever`
- See how graph-enhanced context improves answer quality

**Expected outcome:** Understanding of how to leverage graph relationships for richer, more contextual retrieval that produces better answers.

---

## Notebook 5: Full-Text Search

Vector search finds content by meaning, but sometimes you need **exact term matching** — for specific component IDs, standard references, or precise terminology.

### Full-Text Indexes

Neo4j supports full-text indexes powered by Apache Lucene, providing:
- **Basic search**: Find exact term matches
- **Fuzzy matching**: Tolerate typos (`battrey~` → `battery`)
- **Wildcards**: Match patterns (`therm*` → `thermal`, `thermistor`)
- **Boolean operators**: Combine terms (`thermal AND management`, `cooling OR thermal`)

### Run the Notebook

**To learn full-text search, run [`05_fulltext_search.ipynb`](05_fulltext_search.ipynb)**

In this notebook, you will:
- Create full-text indexes on chunk text and entity names
- Perform basic, fuzzy, wildcard, and boolean searches
- Search entity names (Components, Requirements) by partial match
- Combine full-text search with graph traversal
- Understand when to use full-text vs. vector search

**Expected outcome:** Working full-text indexes and understanding of keyword-based search patterns.

---

## Notebook 6: Hybrid Search

The most powerful retrieval approach combines **vector search** (semantic) with **full-text search** (keyword) in a single query using the `HybridRetriever`.

### HybridRetriever

```python
from neo4j_graphrag.retrievers import HybridRetriever

retriever = HybridRetriever(
    driver=driver,
    vector_index_name="requirement_embeddings",
    fulltext_index_name="requirement_text",
    embedder=embedder
)
```

The `alpha` parameter controls the balance: `1.0` = pure vector, `0.0` = pure full-text, `0.5` = balanced.

### Run the Notebook

**To build hybrid search, run [`06_hybrid_search.ipynb`](06_hybrid_search.ipynb)**

In this notebook, you will:
- Initialize `HybridRetriever` combining vector and full-text search
- Tune the `alpha` parameter to balance semantic vs. keyword matching
- Use `HybridCypherRetriever` for graph-enhanced hybrid search
- Build a complete GraphRAG pipeline with hybrid retrieval
- Experiment with queries that benefit from both search approaches

**Expected outcome:** A complete hybrid search pipeline that handles both conceptual and term-specific queries.

---

## Retriever Selection Guide

| Scenario | Recommended Retriever |
|----------|----------------------|
| Simple semantic Q&A | `VectorRetriever` |
| Need component/requirement context | `VectorCypherRetriever` |
| Specific terms, IDs, standards | `HybridRetriever` |
| Best of all approaches | `HybridCypherRetriever` |

---

## Key Concepts Reference

| Concept | Description |
|---------|-------------|
| **Chunk** | A segment of text small enough for embedding and retrieval |
| **Embedding** | A vector (list of floats) capturing semantic meaning |
| **Vector Index** | Neo4j index enabling fast similarity search |
| **Full-Text Index** | Neo4j index enabling keyword-based search with Lucene |
| **Retriever** | Component that fetches relevant data from Neo4j |
| **top_k** | Number of most similar results to return |
| **alpha** | Balance between vector (1.0) and full-text (0.0) in hybrid search |
| **Retrieval Query** | Custom Cypher appended after vector search |

## Troubleshooting

### "Could not import boto3"
```bash
pip install boto3
```

### Embedding dimension mismatch
Ensure your vector index dimensions match the embedder output:
- Amazon Titan V2: 1024 dimensions
- OpenAI text-embedding-3-large: 3072 dimensions
- OpenAI text-embedding-3-small: 1536 dimensions

### Neo4j connection issues
1. Verify `NEO4J_URI` starts with `neo4j+s://`
2. Check your Aura instance is running
3. Confirm credentials are correct

## Next Steps

**This completes Part 2 - Introduction to Agents and GraphRAG with Neo4j.**

To continue, proceed to **Part 3 - Advanced Agents and API Integration**:

[Lab 6 - Neo4j MCP Agent](../Lab_6_Neo4j_MCP_Agent) - Build a LangGraph agent that connects to Neo4j through the Model Context Protocol (MCP), enabling natural language interaction with your knowledge graph.

## Additional Resources

- [neo4j-graphrag Documentation](https://neo4j.com/docs/neo4j-graphrag-python/)
- [GraphRAG Manifesto](https://neo4j.com/blog/graphrag-manifesto/)
- [Neo4j Vector Index Documentation](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)
