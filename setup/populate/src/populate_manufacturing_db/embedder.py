"""Bedrock Titan Embed v2 integration: embed Requirement and Defect descriptions."""

from __future__ import annotations

import json
import time

import boto3
from neo4j import Driver

from .config import Settings

# Bedrock rate-limit-friendly batch size (sequential calls).
EMBED_BATCH_SIZE = 25


def get_bedrock_client(settings: Settings):
    """Create a Bedrock Runtime client."""
    return boto3.client("bedrock-runtime", region_name=settings.region)


def embed_text(client, model_id: str, text: str) -> list[float]:
    """Embed a single text using Bedrock Titan Embed v2."""
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True,
        }),
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def _embed_and_store(
    driver: Driver,
    client,
    model_id: str,
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
        updates = []
        for row in batch:
            embedding = embed_text(client, model_id, row["text"])
            updates.append({"id": row["id"], "embedding": embedding})

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
    client = get_bedrock_client(settings)
    model_id = settings.embedding_model_id

    print(f"Using model: {model_id} (region: {settings.region})\n")

    start = time.monotonic()

    req_count = _embed_and_store(
        driver, client, model_id,
        label="Requirement",
        id_prop="requirement_id",
        text_prop="description",
    )
    print(f"  [OK] Embedded {req_count} Requirement descriptions.\n")

    defect_count = _embed_and_store(
        driver, client, model_id,
        label="Defect",
        id_prop="defect_id",
        text_prop="description",
    )
    print(f"  [OK] Embedded {defect_count} Defect descriptions.\n")

    elapsed = time.monotonic() - start
    total = req_count + defect_count
    print(f"Embedding complete: {total} nodes in {elapsed:.1f}s.")
