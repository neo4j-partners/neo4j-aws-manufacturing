"""Retriever construction and schema expectations for Lab 5 validation."""

from __future__ import annotations

from dataclasses import dataclass

from neo4j import Driver, GraphDatabase
from neo4j_graphrag.embeddings import BedrockEmbeddings
from neo4j_graphrag.llm import BedrockLLM
from neo4j_graphrag.retrievers import (
    HybridCypherRetriever,
    HybridRetriever,
    VectorCypherRetriever,
    VectorRetriever,
)

from .config import Settings

# ── Expected Lab 5 Schema ──────────────────────────────────────────────────

EXPECTED_NODE_COUNTS = {
    "Product": 1,
    "TechnologyDomain": 4,
    "Component": 12,
    "Requirement": 70,
    "Chunk": 1,  # at least 1; exact count varies by chunking params
}

EXPECTED_REL_TYPES = [
    "PRODUCT_HAS_DOMAIN",
    "DOMAIN_HAS_COMPONENT",
    "COMPONENT_HAS_REQ",
    "HAS_CHUNK",
    "NEXT_CHUNK",
]

EXPECTED_VECTOR_INDEXES = [
    # (index_name, label, property, dimensions)
    ("requirement_embeddings", "Chunk", "embedding", 1024),
]

EXPECTED_FULLTEXT_INDEXES = [
    "requirement_text",
    "search_entities",
]

# ── Cypher retrieval queries (from Lab 5 notebooks 04 and 06) ──────────

CONTEXT_QUERY = """\
MATCH (node)<-[:HAS_CHUNK]-(req:Requirement)
OPTIONAL MATCH (comp:Component)-[:COMPONENT_HAS_REQ]->(req)
OPTIONAL MATCH (prev:Chunk)-[:NEXT_CHUNK]->(node)
OPTIONAL MATCH (node)-[:NEXT_CHUNK]->(next:Chunk)
WITH node, req, comp, prev, next
RETURN
    'Component: ' + COALESCE(comp.name, 'N/A') + ' (' + COALESCE(comp.description, '') + ')' +
    '\\nRequirement: ' + COALESCE(req.name, 'N/A') +
    '\\nContent: ' + COALESCE(prev.text + ' ', '') + node.text + COALESCE(' ' + next.text, '')
    AS context,
    req.name AS requirement_name,
    node.index AS center_chunk_index"""


@dataclass
class Retrievers:
    """Container for all retriever instances and shared resources."""

    driver: Driver
    embedder: BedrockEmbeddings
    llm: BedrockLLM
    vector: VectorRetriever
    vector_cypher: VectorCypherRetriever
    hybrid: HybridRetriever
    hybrid_cypher: HybridCypherRetriever

    def close(self):
        self.driver.close()


def build_retrievers(settings: Settings) -> Retrievers:
    """Build all 4 retriever types used in Lab 5."""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    driver.verify_connectivity()

    embedder = BedrockEmbeddings(
        model_id=settings.embedding_model_id,
        region_name=settings.region,
    )

    llm = BedrockLLM(
        model_id=settings.model_id,
        region_name=settings.region,
    )

    vector = VectorRetriever(
        driver=driver,
        index_name="requirement_embeddings",
        embedder=embedder,
        return_properties=["text"],
    )

    vector_cypher = VectorCypherRetriever(
        driver=driver,
        index_name="requirement_embeddings",
        embedder=embedder,
        retrieval_query=CONTEXT_QUERY,
    )

    hybrid = HybridRetriever(
        driver=driver,
        vector_index_name="requirement_embeddings",
        fulltext_index_name="requirement_text",
        embedder=embedder,
        return_properties=["text"],
    )

    hybrid_cypher = HybridCypherRetriever(
        driver=driver,
        vector_index_name="requirement_embeddings",
        fulltext_index_name="requirement_text",
        embedder=embedder,
        retrieval_query=CONTEXT_QUERY,
    )

    return Retrievers(
        driver=driver,
        embedder=embedder,
        llm=llm,
        vector=vector,
        vector_cypher=vector_cypher,
        hybrid=hybrid,
        hybrid_cypher=hybrid_cypher,
    )
