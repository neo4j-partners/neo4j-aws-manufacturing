"""OpenAI embedding integration: embed Requirement and Defect descriptions."""

from __future__ import annotations

import time

from openai import OpenAI
from neo4j import Driver

from .config import Settings

# OpenAI supports up to ~8k inputs per batch; we use a smaller size
# to keep Neo4j write transactions manageable.
EMBED_BATCH_SIZE = 100

# Default model and dimensions.
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMS = 1536


def get_openai_client(settings: Settings) -> OpenAI:
    """Create an OpenAI client."""
    return OpenAI(api_key=settings.openai_api_key.get_secret_value())


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the OpenAI embeddings API."""
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=texts,
        dimensions=OPENAI_EMBEDDING_DIMS,
    )
    return [item.embedding for item in response.data]


def embed_text(client: OpenAI, text: str) -> list[float]:
    """Embed a single text using the OpenAI embeddings API."""
    return embed_texts(client, [text])[0]


def _embed_and_store(
    driver: Driver,
    client: OpenAI,
    label: str,
    id_prop: str,
    text_prop: str,
) -> int:
    """Fetch nodes, embed their text property, and store embeddings back.

    Returns the number of nodes embedded.
    """
    # Fetch all nodes that have a non-empty text property and no embedding yet.
    records, _, _ = driver.execute_query(
        f"MATCH (n:{label}) "
        f"WHERE n.{text_prop} IS NOT NULL AND n.{text_prop} <> '' "
        f"AND n.embedding IS NULL "
        f"RETURN n.{id_prop} AS id, n.{text_prop} AS text"
    )

    if not records:
        print(f"  No {label} nodes need embedding (already embedded or no text).")
        return 0

    total = len(records)
    print(f"  Embedding {total} {label} descriptions...")

    # Process in batches.
    for i in range(0, total, EMBED_BATCH_SIZE):
        batch = records[i : i + EMBED_BATCH_SIZE]
        texts = [row["text"] for row in batch]
        embeddings = embed_texts(client, texts)

        updates = [
            {"id": row["id"], "embedding": emb}
            for row, emb in zip(batch, embeddings)
        ]

        # Write batch back to Neo4j.
        driver.execute_query(
            f"UNWIND $batch AS row "
            f"MATCH (n:{label} {{{id_prop}: row.id}}) "
            f"SET n.embedding = row.embedding",
            batch=updates,
        )

        progress = min(i + EMBED_BATCH_SIZE, total)
        print(f"  Progress: {progress}/{total} ({100 * progress // total}%)", end="\r")

    print()
    return total


def embed_descriptions(driver: Driver, settings: Settings) -> None:
    """Generate embeddings for Requirement and Defect description fields."""
    client = get_openai_client(settings)

    print(f"Using model: {OPENAI_EMBEDDING_MODEL} ({OPENAI_EMBEDDING_DIMS} dims)\n")

    start = time.monotonic()

    req_count = _embed_and_store(
        driver, client,
        label="Requirement",
        id_prop="requirement_id",
        text_prop="description",
    )
    print(f"  [OK] Embedded {req_count} Requirement descriptions.\n")

    defect_count = _embed_and_store(
        driver, client,
        label="Defect",
        id_prop="defect_id",
        text_prop="description",
    )
    print(f"  [OK] Embedded {defect_count} Defect descriptions.\n")

    elapsed = time.monotonic() - start
    total = req_count + defect_count
    print(f"Embedding complete: {total} nodes in {elapsed:.1f}s.")
