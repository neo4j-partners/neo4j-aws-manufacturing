"""CLI entry point for populate-manufacturing-db."""

from __future__ import annotations

import sys
import time
from collections.abc import Generator
from contextlib import contextmanager

import typer
from neo4j import Driver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable

from .config import Settings
from .loader import clear_database, load_nodes, load_relationships, verify
from .schema import create_constraints, create_indexes, create_vector_indexes

app = typer.Typer(
    name="populate-manufacturing-db",
    help="Load the Manufacturing Product Development dataset into a Neo4j Aura instance.",
    add_completion=False,
)


def _fmt_elapsed(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


@contextmanager
def _connect(settings: Settings) -> Generator[Driver, None, None]:
    """Create a Neo4j driver, verify connectivity, and close on exit."""
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )
    try:
        driver.verify_connectivity()
    except (ServiceUnavailable, OSError) as exc:
        driver.close()
        print(f"[FAIL] Cannot connect to {settings.neo4j_uri}")
        print(f"       {exc}")
        print("\nCheck that the Neo4j instance is running and reachable.")
        sys.exit(1)
    try:
        print("[OK] Connected.\n")
        yield driver
    finally:
        driver.close()


@app.command()
def load() -> None:
    """Load all CSV data, generate embeddings, and create indexes in a single pipeline."""
    from .embedder import embed_descriptions

    settings = Settings()  # type: ignore[call-arg]
    start = time.monotonic()

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        print("Creating constraints...")
        create_constraints(driver)
        print("\nCreating indexes...")
        create_indexes(driver)
        print()

        load_nodes(driver, settings.data_dir)
        print()
        load_relationships(driver, settings.data_dir)
        print()

        embed_descriptions(driver, settings)

        print("\nCreating vector indexes...")
        create_vector_indexes(driver)

        verify(driver)

    elapsed = time.monotonic() - start
    print(f"\nDone in {_fmt_elapsed(elapsed)}.")


@app.command("verify")
def verify_cmd() -> None:
    """Print node and relationship counts (read-only)."""
    settings = Settings()  # type: ignore[call-arg]

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        verify(driver)


@app.command("clean")
def clean_cmd() -> None:
    """Clear all nodes and relationships from the database."""
    settings = Settings()  # type: ignore[call-arg]

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        clear_database(driver)

    print("\nDone.")


@app.command("samples")
def samples_cmd() -> None:
    """Run sample queries showcasing the knowledge graph (read-only)."""
    from .samples import run_all_samples

    settings = Settings()  # type: ignore[call-arg]

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        run_all_samples(driver, settings, sample_size=settings.sample_size)


@app.command("test-queries")
def test_queries_cmd(
    top_k: int = typer.Option(5, help="Number of results per query."),
) -> None:
    """Run semantic similarity and hybrid search test queries (requires OpenAI API key)."""
    from .test_queries import run_test_queries

    settings = Settings()  # type: ignore[call-arg]
    start = time.monotonic()

    print(f"Connecting to {settings.neo4j_uri}...")
    with _connect(settings) as driver:
        run_test_queries(driver, settings, top_k=top_k)

    elapsed = time.monotonic() - start
    print(f"Done in {_fmt_elapsed(elapsed)}.")


if __name__ == "__main__":
    app()
