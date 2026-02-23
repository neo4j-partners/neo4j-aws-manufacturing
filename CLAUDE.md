# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a hands-on workshop teaching GraphRAG (Graph Retrieval-Augmented Generation) using Neo4j and AWS Bedrock. The workshop uses an automotive manufacturing dataset (products, components, requirements, defects, test cases) and progresses from no-code tools to building custom agents.

## Workshop Structure

- **Part 1 (Labs 0-2)**: No-code exploration using Neo4j Aura console and Aura Agents visual builder
- **Part 2 (Labs 4-5)**: Python-based GraphRAG with LangGraph and neo4j-graphrag library
- **Part 3 (Labs 6-7)**: Advanced API integration and MCP (Model Context Protocol) agents

## Key Configuration

All credentials are stored in `CONFIG.txt` at the project root (gitignored). The file uses dotenv format:

```
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=...
MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
REGION=us-west-2
```

## Lab Code Patterns

### Lab 4 - Basic LangGraph Agent
Location: `Lab_4_Intro_to_Bedrock_and_Agents/basic_langgraph_agent.ipynb`

Uses `ChatBedrockConverse` from langchain-aws with the ReAct pattern:
```python
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
```

For cross-region inference profiles (MODEL_ID starting with `us.` or `global.`), derive base_model_id:
```python
if MODEL_ID.startswith("us.anthropic."):
    BASE_MODEL_ID = MODEL_ID.replace("us.anthropic.", "anthropic.")
```

### Lab 5 - GraphRAG
Location: `Lab_5_GraphRAG/`

Six notebooks covering data loading, embeddings, vector retrieval, graph-enhanced retrieval, full-text search, and hybrid search.

Uses a forked neo4j-graphrag with Bedrock support:
```bash
pip install "neo4j-graphrag[bedrock] @ git+https://github.com/neo4j-partners/neo4j-graphrag-python.git@bedrock-embeddings"
```

Key utility classes in `data_utils.py`:
- `Neo4jConnection`: Manages driver connection using `Neo4jConfig` (pydantic-settings)
- `CSVLoader`: Loads structured data from `TransformedData/` CSV files
- `DataLoader`: Loads text data files (e.g., `manufacturing_data.txt`)
- `get_embedder()`: Returns `BedrockEmbeddings` configured from environment
- `get_llm()`: Returns `BedrockLLM` configured from environment
- `split_text()`: Wraps `FixedSizeSplitter` with async handling for Jupyter

Graph structure for manufacturing traceability:
```
(:Product) -[:PRODUCT_HAS_DOMAIN]-> (:TechnologyDomain) -[:DOMAIN_HAS_COMPONENT]-> (:Component)
(:Component) -[:COMPONENT_HAS_REQ]-> (:Requirement) -[:HAS_CHUNK]-> (:Chunk) -[:NEXT_CHUNK]-> (:Chunk)
```

### Lab 6 - MCP Agent
Location: `Lab_6_Neo4j_MCP_Agent/`

Two implementations:
- `neo4j_langgraph_mcp_agent.ipynb`: LangGraph + langchain-mcp-adapters
- `neo4j_strands_mcp_agent.ipynb`: Alternative using Strands framework

MCP connection pattern:
```python
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
```

### Lab 7 - Aura Agents API
Location: `Lab_7_Aura_Agents_API/aura_agent_client.ipynb`

Contains `AuraAgentClient` class for OAuth2 authentication and agent invocation:
- Token URL: `https://api.neo4j.io/oauth/token`
- Uses client credentials flow with Basic Auth
- Tokens cached and auto-refreshed on 401

## Knowledge Graph Schema

The manufacturing dataset includes:
- **Nodes**: Product, TechnologyDomain, Component, Requirement, TestSet, TestCase, Defect, Change, Chunk
- **Relationships**: PRODUCT_HAS_DOMAIN, DOMAIN_HAS_COMPONENT, COMPONENT_HAS_REQ, TESTED_WITH, CONTAINS_TEST_CASE, DETECTED, CHANGE_AFFECTS_REQ, HAS_CHUNK, NEXT_CHUNK
- **Vector Index**: `requirement_embeddings` on Chunk.embedding (1024 dims for Titan)
- **Fulltext Indexes**: `requirement_text` (on Chunk.text), `search_entities` (on Component/Requirement names and descriptions)

## Manufacturing Data

Structured CSV data lives in `TransformedData/`:
- `products.csv`, `technology_domains.csv`, `components.csv` — Entity data
- `product_technology_domains.csv`, `technology_domains_components.csv` — Junction tables
- `requirements.csv`, `test_sets.csv`, `test_cases.csv`, `defects.csv`, `changes.csv` — Traceability data
- Additional junction tables for relationships between these entities

Key entities: R2D2 product, HVB_3900 (High-Voltage Battery), Electric Powertrain / Chassis / Body / Infotainment technology domains.

## Running Notebooks

The notebooks are designed for AWS SageMaker Studio but work locally with:
1. Configure `CONFIG.txt` with Neo4j and AWS credentials
2. Install dependencies per notebook (uses `%pip install`)
3. Ensure AWS credentials are configured for Bedrock access

## Dependencies

Lab 5 uses `pyproject.toml` at `Lab_5_GraphRAG/src/pyproject.toml`:
- Python 3.11+
- neo4j-graphrag[bedrock] (from neo4j-partners fork)
- python-dotenv, pydantic-settings, nest-asyncio
