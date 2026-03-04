"""CLI entry point for the GraphRAG validator."""

from __future__ import annotations

import sys
import time

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from .config import Settings

app = typer.Typer(
    name="graphrag-validator",
    help="Validate Lab 5 GraphRAG setup (Neo4j + AWS Bedrock).",
    add_completion=False,
)

console = Console()


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------


class TestRunner:
    """Tracks pass/fail counts and timing."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total_time = 0.0

    def section(self, title: str) -> None:
        console.print(Rule(f"[bold]{title}"))

    def check(self, name: str, condition: bool, detail: str = "") -> bool:
        if condition:
            self.passed += 1
            console.print(f"  [green]PASS[/green]  {name}")
        else:
            self.failed += 1
            msg = f"  [red]FAIL[/red]  {name}"
            if detail:
                msg += f" — {detail}"
            console.print(msg)
        return condition

    def run_timed(self, name: str, fn, *args, **kwargs):
        """Run fn, check it doesn't raise, return its result."""
        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            elapsed = time.monotonic() - start
            self.total_time += elapsed
            self.passed += 1
            console.print(f"  [green]PASS[/green]  {name} [dim]({elapsed:.1f}s)[/dim]")
            return result
        except Exception as exc:
            elapsed = time.monotonic() - start
            self.total_time += elapsed
            self.failed += 1
            console.print(f"  [red]FAIL[/red]  {name} — {exc} [dim]({elapsed:.1f}s)[/dim]")
            return None

    def summary(self) -> None:
        console.print(Rule("[bold]Results"))
        console.print(
            f"  [green]{self.passed} passed[/green]  "
            f"[red]{self.failed} failed[/red]  "
            f"({self.total_time:.1f}s total)\n"
        )


# ---------------------------------------------------------------------------
# Phase 1: Database preflight
# ---------------------------------------------------------------------------


def _test_preflight(driver, t: TestRunner) -> bool:
    """Verify Lab 5 schema: nodes, relationships, vector/fulltext indexes, embeddings."""
    from .retrievers import (
        EXPECTED_FULLTEXT_INDEXES,
        EXPECTED_NODE_COUNTS,
        EXPECTED_REL_TYPES,
        EXPECTED_VECTOR_INDEXES,
    )

    t.section("Phase 1: Database Preflight")
    all_ok = True

    # -- Node counts --
    console.print("\n  [bold]Node Counts[/bold]")
    for label, expected in EXPECTED_NODE_COUNTS.items():
        rows, _, _ = driver.execute_query(f"MATCH (n:{label}) RETURN count(n) AS c")
        actual = rows[0]["c"] if rows else 0
        ok = actual >= expected
        t.check(f"{label}: {actual} (expected >= {expected})", ok, f"got {actual}")
        if not ok:
            all_ok = False

    # -- Relationship types --
    console.print("\n  [bold]Relationship Types[/bold]")
    rows, _, _ = driver.execute_query(
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
    )
    existing_types = {r["relationshipType"] for r in rows}
    for rel_type in EXPECTED_REL_TYPES:
        ok = rel_type in existing_types
        t.check(rel_type, ok, "missing relationship type")
        if not ok:
            all_ok = False

    # -- Vector indexes --
    console.print("\n  [bold]Vector Indexes[/bold]")
    rows, _, _ = driver.execute_query(
        "SHOW INDEXES YIELD name, type, options WHERE type = 'VECTOR'"
    )
    vector_map = {}
    for r in rows:
        name = r.get("name")
        options = r.get("options") or {}
        config = options.get("indexConfig") or {}
        dims = config.get("vector.dimensions")
        vector_map[name] = dims

    for name, label, prop, expected_dims in EXPECTED_VECTOR_INDEXES:
        exists = name in vector_map
        t.check(f"{name} exists", exists, "missing vector index")
        if exists:
            t.check(
                f"{name} dimensions = {expected_dims}",
                vector_map[name] == expected_dims,
                f"got {vector_map[name]}",
            )
        else:
            all_ok = False

    # -- Fulltext indexes --
    console.print("\n  [bold]Fulltext Indexes[/bold]")
    rows, _, _ = driver.execute_query(
        "SHOW INDEXES YIELD name, type WHERE type = 'FULLTEXT'"
    )
    fulltext_names = {r["name"] for r in rows}
    for idx_name in EXPECTED_FULLTEXT_INDEXES:
        ok = idx_name in fulltext_names
        t.check(f"{idx_name} exists", ok, "missing fulltext index")
        if not ok:
            all_ok = False

    # -- Embeddings populated on Chunk nodes --
    console.print("\n  [bold]Embeddings[/bold]")
    rows, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c) AS c"
    )
    count = rows[0]["c"] if rows else 0
    t.check(f"Chunk nodes with embeddings: {count}", count > 0, "no embeddings found")
    if count > 0:
        rows2, _, _ = driver.execute_query(
            "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL "
            "RETURN size(c.embedding) AS dims LIMIT 1"
        )
        dims = rows2[0]["dims"] if rows2 else 0
        t.check(f"Chunk embedding dimensions = 1024", dims == 1024, f"got {dims}")

    console.print()
    return all_ok


# ---------------------------------------------------------------------------
# Phase 2: Direct retriever tests
# ---------------------------------------------------------------------------


def _test_retrievers(retrievers, t: TestRunner) -> None:
    """Call each retriever directly and validate response content."""
    t.section("Phase 2: Direct Retriever Tests")

    # -- VectorRetriever --
    console.print("\n  [bold]VectorRetriever[/bold]")

    def _vector_search():
        return retrievers.vector.search(query_text="thermal management", top_k=5)

    result = t.run_timed("search 'thermal management'", _vector_search)
    if result:
        t.check("returns results", len(result.items) > 0, "no items returned")
        if result.items:
            content = " ".join(str(item.content).lower() for item in result.items)
            thermal_terms = {"thermal", "cooling", "heat", "temperature"}
            matches = thermal_terms & set(content.split())
            t.check(
                "results are semantically relevant (thermal/cooling/heat)",
                len(matches) > 0,
                f"found terms: {matches or 'none'}",
            )

    def _vector_search_safety():
        return retrievers.vector.search(query_text="safety monitoring", top_k=5)

    result2 = t.run_timed("search 'safety monitoring'", _vector_search_safety)
    if result2:
        t.check("returns results for safety query", len(result2.items) > 0)

    # -- VectorCypherRetriever --
    console.print("\n  [bold]VectorCypherRetriever[/bold]")

    def _vector_cypher_search():
        return retrievers.vector_cypher.search(query_text="thermal management", top_k=3)

    result = t.run_timed("search 'thermal management'", _vector_cypher_search)
    if result:
        t.check("returns results", len(result.items) > 0, "no items returned")
        if result.items:
            content = str(result.items[0].content)
            has_component = "Component:" in content or "component" in content.lower()
            has_requirement = "Requirement:" in content or "requirement" in content.lower()
            t.check(
                "includes component context",
                has_component,
                f"content preview: {content[:150]}",
            )
            t.check(
                "includes requirement context",
                has_requirement,
                f"content preview: {content[:150]}",
            )

    # -- Fulltext search (raw Cypher) --
    console.print("\n  [bold]Fulltext Search[/bold]")

    def _fulltext_exact():
        rows, _, _ = retrievers.driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $query) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            query="thermal",
        )
        return rows

    result = t.run_timed("exact search 'thermal'", _fulltext_exact)
    if result:
        t.check("returns results", len(result) > 0)
        if result:
            t.check(
                "result contains 'thermal'",
                "thermal" in result[0]["text"].lower(),
            )

    def _fulltext_fuzzy():
        rows, _, _ = retrievers.driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $query) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            query="battrey~",
        )
        return rows

    result = t.run_timed("fuzzy search 'battrey~'", _fulltext_fuzzy)
    if result:
        t.check("fuzzy matches 'battery'", len(result) > 0)

    def _fulltext_wildcard():
        rows, _, _ = retrievers.driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $query) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            query="therm*",
        )
        return rows

    result = t.run_timed("wildcard search 'therm*'", _fulltext_wildcard)
    if result:
        t.check("wildcard returns results", len(result) > 0)

    def _fulltext_boolean():
        rows, _, _ = retrievers.driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $query) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            query="thermal AND management",
        )
        return rows

    result = t.run_timed("boolean search 'thermal AND management'", _fulltext_boolean)
    if result:
        t.check("boolean returns results", len(result) > 0)

    # -- Entity fulltext index --
    console.print("\n  [bold]Entity Fulltext Search[/bold]")

    def _entity_search():
        rows, _, _ = retrievers.driver.execute_query(
            "CALL db.index.fulltext.queryNodes('search_entities', $query) "
            "YIELD node, score RETURN node.name AS name, score LIMIT 3",
            query="battery",
        )
        return rows

    result = t.run_timed("entity search 'battery'", _entity_search)
    if result:
        t.check("returns entity results", len(result) > 0)

    # -- HybridRetriever --
    console.print("\n  [bold]HybridRetriever[/bold]")

    def _hybrid_search():
        return retrievers.hybrid.search(
            query_text="battery cooling specifications", top_k=5
        )

    result = t.run_timed("search 'battery cooling specifications'", _hybrid_search)
    if result:
        t.check("returns results", len(result.items) > 0, "no items returned")

    # -- HybridCypherRetriever --
    console.print("\n  [bold]HybridCypherRetriever[/bold]")

    def _hybrid_cypher_search():
        return retrievers.hybrid_cypher.search(
            query_text="energy density specifications", top_k=3
        )

    result = t.run_timed("search 'energy density specifications'", _hybrid_cypher_search)
    if result:
        t.check("returns results", len(result.items) > 0, "no items returned")
        if result.items:
            content = str(result.items[0].content)
            has_context = "Component:" in content or "Requirement:" in content
            t.check("includes graph context", has_context, f"content preview: {content[:150]}")

    console.print()


# ---------------------------------------------------------------------------
# Phase 3: GraphRAG integration (retriever + LLM generation)
# ---------------------------------------------------------------------------

GRAPHRAG_QUESTIONS = [
    (
        "VectorRetriever",
        "What are the thermal management requirements for the battery?",
        ["thermal", "cool", "heat", "temperature"],
    ),
    (
        "HybridCypherRetriever",
        "What safety standards must the battery system comply with?",
        ["safety"],
    ),
    (
        "HybridCypherRetriever",
        "What are the energy density specifications for battery cells?",
        ["energy", "density", "cell"],
    ),
]


def _test_graphrag(retrievers, t: TestRunner) -> None:
    """Run questions through full GraphRAG pipeline and validate responses."""
    from neo4j_graphrag.generation import GraphRAG

    t.section("Phase 3: GraphRAG Integration (LLM generation)")

    rag_vector = GraphRAG(llm=retrievers.llm, retriever=retrievers.vector)
    rag_hybrid_cypher = GraphRAG(llm=retrievers.llm, retriever=retrievers.hybrid_cypher)

    for i, (retriever_name, question, expected_terms) in enumerate(GRAPHRAG_QUESTIONS, 1):
        console.print(f"\n  [bold]{i}/{len(GRAPHRAG_QUESTIONS)} {retriever_name}[/bold]")
        console.print(f"  [blue]Q:[/blue] {question}")

        rag = rag_vector if retriever_name == "VectorRetriever" else rag_hybrid_cypher

        start = time.monotonic()
        try:
            response = rag.search(question, retriever_config={"top_k": 3})
            elapsed = time.monotonic() - start
            t.total_time += elapsed

            answer = response.answer
            t.check(f"got response ({elapsed:.1f}s)", bool(answer))

            answer_lower = answer.lower()
            matched = [term for term in expected_terms if term.lower() in answer_lower]
            t.check(
                f"response contains expected terms ({matched})",
                len(matched) > 0,
                f"none of {expected_terms} found in response",
            )

            preview = answer[:150] + "..." if len(answer) > 150 else answer
            console.print(f"  [dim]{preview}[/dim]")

        except Exception as exc:
            elapsed = time.monotonic() - start
            t.total_time += elapsed
            t.check(f"no error ({elapsed:.1f}s)", False, str(exc))

    console.print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def test() -> None:
    """Run comprehensive Lab 5 GraphRAG validation suite."""
    from neo4j import GraphDatabase

    from .retrievers import build_retrievers

    settings = Settings()  # type: ignore[call-arg]
    t = TestRunner()

    console.print(f"\nConnecting to {settings.neo4j_uri}...", style="dim")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    driver.verify_connectivity()
    console.print("[green]Connected.[/green]\n")

    # Phase 1: Preflight (no Bedrock API calls needed)
    preflight_ok = _test_preflight(driver, t)
    driver.close()

    if not preflight_ok:
        console.print(
            "[yellow]Preflight issues detected — continuing with retriever tests anyway.[/yellow]\n"
        )

    # Phase 2: Direct retriever tests (uses Bedrock embeddings)
    console.print("Initializing retrievers...", style="dim")
    try:
        retrievers = build_retrievers(settings)
        console.print("[green]Retrievers ready.[/green]\n")
    except Exception as exc:
        t.failed += 1
        console.print(f"  [red]FAIL[/red]  Failed to initialize retrievers — {exc}\n")
        t.summary()
        raise SystemExit(1)

    _test_retrievers(retrievers, t)

    # Phase 3: GraphRAG integration (uses Bedrock LLM)
    _test_graphrag(retrievers, t)

    retrievers.close()

    # Summary
    t.summary()
    if t.failed:
        raise SystemExit(1)


@app.command()
def chat() -> None:
    """Start an interactive chat session using GraphRAG with HybridCypherRetriever."""
    from neo4j_graphrag.generation import GraphRAG

    from .retrievers import build_retrievers

    settings = Settings()  # type: ignore[call-arg]

    console.print(f"\nConnecting to {settings.neo4j_uri}...", style="dim")
    try:
        retrievers = build_retrievers(settings)
    except Exception as exc:
        console.print(f"[red]Failed to initialize: {exc}[/red]")
        sys.exit(1)

    rag = GraphRAG(llm=retrievers.llm, retriever=retrievers.hybrid_cypher)
    console.print("[green]GraphRAG ready.[/green] Type your question or 'quit' to exit.\n")

    try:
        while True:
            try:
                question = console.input("[bold blue]You:[/bold blue] ").strip()
            except EOFError:
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                break

            try:
                response = rag.search(question, retriever_config={"top_k": 3})
                if response.answer:
                    console.print()
                    console.print(Markdown(response.answer))
                    console.print()
                else:
                    console.print("[dim]No response.[/dim]\n")
            except Exception as exc:
                console.print(f"\n[red]Error: {exc}[/red]\n")
    finally:
        retrievers.close()
        console.print("\n[dim]Goodbye.[/dim]")


if __name__ == "__main__":
    app()
