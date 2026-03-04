"""Data loading, graph creation, embeddings, and index management (notebooks 01 + 02)."""

from __future__ import annotations

import asyncio
import csv
from pathlib import Path

from neo4j import Driver
from neo4j_graphrag.embeddings import BedrockEmbeddings
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import (
    FixedSizeSplitter,
)
from neo4j_graphrag.indexes import create_vector_index

_PKG_DIR = Path(__file__).resolve().parent
# src/graphrag_validator -> src -> solutions_bedrock -> setup -> repo root
_REPO_ROOT = _PKG_DIR.parent.parent.parent.parent
_CSV_DIR = _REPO_ROOT / "TransformedData"
_TEXT_FILE = _REPO_ROOT / "Lab_5_GraphRAG" / "manufacturing_data.txt"


# ── CSV data loading ─────────────────────────────────────────────────────────


def load_csv(filename: str) -> list[dict]:
    """Load a CSV file from TransformedData/ and return list of row dicts."""
    filepath = _CSV_DIR / filename
    with open(filepath, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_manufacturing_text() -> str:
    """Load the manufacturing requirement text from Lab_5_GraphRAG/."""
    return _TEXT_FILE.read_text().strip()


# ── Text splitting ───────────────────────────────────────────────────────────


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Split text into chunks using FixedSizeSplitter (same as data_utils.py)."""
    splitter = FixedSizeSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        approximate=True,
    )

    # Handle both Jupyter (running event loop) and regular Python
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        import nest_asyncio

        nest_asyncio.apply()
        result = asyncio.run(splitter.run(text))
    else:
        result = asyncio.run(splitter.run(text))

    return [chunk.text for chunk in result.chunks]


# ── Graph creation (notebook 01) ─────────────────────────────────────────────


def clear_lab5_data(driver: Driver) -> None:
    """Delete Chunk nodes and drop Lab 5-specific indexes, preserving base graph."""
    with driver.session() as session:
        # Drop indexes first
        for idx in ("requirement_embeddings", "requirement_text", "search_entities"):
            session.run(f"DROP INDEX {idx} IF EXISTS")

        # Delete Chunk nodes and their relationships
        session.run("MATCH (c:Chunk) DETACH DELETE c")

        # Delete Requirement nodes and their relationships
        session.run("MATCH (r:Requirement) DETACH DELETE r")


def create_products(driver: Driver, products: list[dict]) -> int:
    """Create Product nodes from CSV data. Uses MERGE to be idempotent."""
    with driver.session() as session:
        for p in products:
            session.run(
                "MERGE (p:Product {product_id: $id}) "
                "SET p.name = $name, p.description = $desc",
                id=p["product_id"],
                name=p["Product Name"],
                desc=p["Description"],
            )
    return len(products)


def create_technology_domains(driver: Driver, domains: list[dict]) -> int:
    """Create TechnologyDomain nodes from CSV data. Uses MERGE to be idempotent."""
    with driver.session() as session:
        for td in domains:
            session.run(
                "MERGE (t:TechnologyDomain {technology_domain_id: $id}) "
                "SET t.name = $name",
                id=td["technology_domain_id"],
                name=td["Technology Domain"],
            )
    return len(domains)


def create_components(driver: Driver, components: list[dict]) -> int:
    """Create Component nodes from CSV data. Uses MERGE to be idempotent."""
    with driver.session() as session:
        for c in components:
            session.run(
                "MERGE (comp:Component {component_id: $id}) "
                "SET comp.name = $name, comp.description = $desc",
                id=c["component_id"],
                name=c["Component"],
                desc=c["Component Description"],
            )
    return len(components)


def create_product_domain_rels(driver: Driver, rels: list[dict]) -> int:
    """Create PRODUCT_HAS_DOMAIN relationships. Uses MERGE to be idempotent."""
    with driver.session() as session:
        for row in rels:
            session.run(
                "MATCH (p:Product {product_id: $pid}) "
                "MATCH (t:TechnologyDomain {technology_domain_id: $tid}) "
                "MERGE (p)-[:PRODUCT_HAS_DOMAIN]->(t)",
                pid=row["product_id"],
                tid=row["technology_domain_id"],
            )
    return len(rels)


def create_domain_component_rels(driver: Driver, rels: list[dict]) -> int:
    """Create DOMAIN_HAS_COMPONENT relationships. Uses MERGE to be idempotent."""
    with driver.session() as session:
        for row in rels:
            session.run(
                "MATCH (t:TechnologyDomain {technology_domain_id: $tid}) "
                "MATCH (c:Component {component_id: $cid}) "
                "MERGE (t)-[:DOMAIN_HAS_COMPONENT]->(c)",
                tid=row["technology_domain_id"],
                cid=row["component_id"],
            )
    return len(rels)


def create_requirement_with_chunks(driver: Driver, req_name: str, chunks: list[str]) -> int:
    """Create Requirement node + Chunk nodes + HAS_CHUNK + NEXT_CHUNK relationships.

    Matches notebook 01 pattern exactly.
    """
    with driver.session() as session:
        # Create Requirement node
        result = session.run(
            "CREATE (r:Requirement {requirement_id: '1_1', name: $name, "
            "description: 'Battery Cell and Module Design'}) "
            "RETURN elementId(r) AS req_id",
            name=req_name,
        )
        req_id = result.single()["req_id"]

        # Link Requirement to Component
        session.run(
            "MATCH (r:Requirement) WHERE elementId(r) = $req_id "
            "MATCH (c:Component {name: 'HVB_3900'}) "
            "CREATE (c)-[:COMPONENT_HAS_REQ]->(r)",
            req_id=req_id,
        )

        # Create Chunk nodes with HAS_CHUNK relationships
        chunk_ids = []
        for index, text in enumerate(chunks):
            result = session.run(
                "MATCH (r:Requirement) WHERE elementId(r) = $req_id "
                "CREATE (c:Chunk {text: $text, index: $index}) "
                "CREATE (r)-[:HAS_CHUNK]->(c) "
                "RETURN elementId(c) AS chunk_id",
                req_id=req_id,
                text=text,
                index=index,
            )
            chunk_ids.append(result.single()["chunk_id"])

        # Create NEXT_CHUNK relationships
        for i in range(len(chunk_ids) - 1):
            session.run(
                "MATCH (c1:Chunk) WHERE elementId(c1) = $id1 "
                "MATCH (c2:Chunk) WHERE elementId(c2) = $id2 "
                "CREATE (c1)-[:NEXT_CHUNK]->(c2)",
                id1=chunk_ids[i],
                id2=chunk_ids[i + 1],
            )

    return len(chunks)


# ── Embeddings (notebook 02) ─────────────────────────────────────────────────


def generate_embeddings(
    embedder: BedrockEmbeddings, chunks: list[str]
) -> list[dict]:
    """Generate embeddings for each chunk text. Returns list of {text, index, embedding}."""
    chunk_data = []
    for i, text in enumerate(chunks):
        embedding = embedder.embed_query(text)
        chunk_data.append({"text": text, "index": i, "embedding": embedding})
    return chunk_data


def store_chunks_with_embeddings(
    driver: Driver, req_name: str, chunk_data: list[dict]
) -> int:
    """Store Requirement + Chunk nodes with embeddings (notebook 02 pattern).

    Creates Requirement, Chunk nodes with embeddings, HAS_CHUNK, and NEXT_CHUNK.
    """
    with driver.session() as session:
        # Create Requirement
        result = session.run(
            "CREATE (r:Requirement {requirement_id: '1_1', name: $name, "
            "description: 'Battery Cell and Module Design'}) "
            "RETURN elementId(r) AS req_id",
            name=req_name,
        )
        req_id = result.single()["req_id"]

        # Link Requirement to Component
        session.run(
            "MATCH (r:Requirement) WHERE elementId(r) = $req_id "
            "MATCH (c:Component {name: 'HVB_3900'}) "
            "CREATE (c)-[:COMPONENT_HAS_REQ]->(r)",
            req_id=req_id,
        )

        # Create Chunks with embeddings and HAS_CHUNK relationships
        for chunk in chunk_data:
            session.run(
                "MATCH (r:Requirement) WHERE elementId(r) = $req_id "
                "CREATE (c:Chunk {text: $text, index: $index, embedding: $embedding}) "
                "CREATE (r)-[:HAS_CHUNK]->(c)",
                req_id=req_id,
                text=chunk["text"],
                index=chunk["index"],
                embedding=chunk["embedding"],
            )

        # Create NEXT_CHUNK relationships
        session.run(
            "MATCH (r:Requirement) WHERE elementId(r) = $req_id "
            "MATCH (r)-[:HAS_CHUNK]->(c:Chunk) "
            "WITH c ORDER BY c.index "
            "WITH collect(c) AS chunks "
            "UNWIND range(0, size(chunks)-2) AS i "
            "WITH chunks[i] AS c1, chunks[i+1] AS c2 "
            "CREATE (c1)-[:NEXT_CHUNK]->(c2)",
            req_id=req_id,
        )

    return len(chunk_data)


# ── Index creation ───────────────────────────────────────────────────────────


def create_vector_idx(driver: Driver, retries: int = 3) -> None:
    """Create the requirement_embeddings vector index (1024 dims, cosine).

    Uses retries on transient connection errors and waits for ONLINE state.
    """
    import time

    for attempt in range(retries):
        try:
            with driver.session() as session:
                session.run("DROP INDEX requirement_embeddings IF EXISTS")
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)

    for attempt in range(retries):
        try:
            create_vector_index(
                driver=driver,
                name="requirement_embeddings",
                label="Chunk",
                embedding_property="embedding",
                dimensions=1024,
                similarity_fn="cosine",
            )
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2)

    # Wait for index to come ONLINE (up to 30s)
    for _ in range(15):
        rows, _, _ = driver.execute_query(
            "SHOW INDEXES YIELD name, type, state "
            "WHERE type = 'VECTOR' AND name = 'requirement_embeddings'"
        )
        if rows and rows[0]["state"] == "ONLINE":
            return
        time.sleep(2)

    state = rows[0]["state"] if rows else "NOT FOUND"
    raise RuntimeError(
        f"Vector index not ONLINE after 30s: {state}"
    )


def create_fulltext_indexes(driver: Driver, retries: int = 3) -> None:
    """Create the requirement_text and search_entities fulltext indexes.

    Uses separate sessions per statement and retries on transient connection errors.
    Waits for indexes to come ONLINE before returning.
    """
    import time

    statements = [
        "DROP INDEX requirement_text IF EXISTS",
        "DROP INDEX search_entities IF EXISTS",
        (
            "CREATE FULLTEXT INDEX requirement_text IF NOT EXISTS "
            "FOR (c:Chunk) ON EACH [c.text]"
        ),
        (
            "CREATE FULLTEXT INDEX search_entities IF NOT EXISTS "
            "FOR (n:Component|Requirement) ON EACH [n.name, n.description]"
        ),
    ]

    for stmt in statements:
        for attempt in range(retries):
            try:
                with driver.session() as session:
                    session.run(stmt)
                break
            except Exception:
                if attempt == retries - 1:
                    raise
                time.sleep(2)

    # Wait for indexes to come ONLINE (up to 30s)
    for _ in range(15):
        rows, _, _ = driver.execute_query(
            "SHOW INDEXES YIELD name, type, state "
            "WHERE type = 'FULLTEXT' AND name IN ['requirement_text', 'search_entities']"
        )
        states = {r["name"]: r["state"] for r in rows}
        if (
            states.get("requirement_text") == "ONLINE"
            and states.get("search_entities") == "ONLINE"
        ):
            return
        time.sleep(2)

    raise RuntimeError(
        f"Fulltext indexes not ONLINE after 30s: {states}"
    )
