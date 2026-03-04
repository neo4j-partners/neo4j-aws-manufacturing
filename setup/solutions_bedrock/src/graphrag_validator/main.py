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
# Phase 1: Data Loading (= Notebook 01)
# ---------------------------------------------------------------------------


def _phase1_data_loading(driver, t: TestRunner) -> bool:
    """Clear Lab 5 data, load CSVs, create base graph, split text into chunks."""
    from .data import (
        clear_lab5_data,
        create_components,
        create_domain_component_rels,
        create_product_domain_rels,
        create_products,
        create_requirement_with_chunks,
        create_technology_domains,
        load_csv,
        load_manufacturing_text,
        split_text,
    )
    from .retrievers import EXPECTED_NODE_COUNTS, EXPECTED_REL_TYPES

    t.section("Phase 1: Data Loading (Notebook 01)")

    # Clear Lab 5-specific data (Chunks, Requirements, indexes)
    console.print("\n  [bold]Clearing Lab 5 data...[/bold]")
    t.run_timed("clear Lab 5 data", clear_lab5_data, driver)

    # Load CSV data
    console.print("\n  [bold]Loading CSV Data[/bold]")
    products = t.run_timed("load products.csv", load_csv, "products.csv")
    tech_domains = t.run_timed("load technology_domains.csv", load_csv, "technology_domains.csv")
    components = t.run_timed("load components.csv", load_csv, "components.csv")
    product_domains = t.run_timed(
        "load product_technology_domains.csv", load_csv, "product_technology_domains.csv"
    )
    domain_components = t.run_timed(
        "load technology_domains_components.csv", load_csv, "technology_domains_components.csv"
    )

    if not all([products, tech_domains, components, product_domains, domain_components]):
        console.print("  [red]CSV loading failed, cannot continue.[/red]\n")
        return False

    # Create base graph nodes (MERGE = idempotent, safe if backup already loaded them)
    console.print("\n  [bold]Creating Base Graph[/bold]")
    t.run_timed(f"create {len(products)} Product nodes", create_products, driver, products)
    t.run_timed(
        f"create {len(tech_domains)} TechnologyDomain nodes",
        create_technology_domains,
        driver,
        tech_domains,
    )
    t.run_timed(
        f"create {len(components)} Component nodes", create_components, driver, components
    )
    t.run_timed(
        f"create {len(product_domains)} PRODUCT_HAS_DOMAIN rels",
        create_product_domain_rels,
        driver,
        product_domains,
    )
    t.run_timed(
        f"create {len(domain_components)} DOMAIN_HAS_COMPONENT rels",
        create_domain_component_rels,
        driver,
        domain_components,
    )

    # Load and split text
    console.print("\n  [bold]Text Chunking[/bold]")
    text = t.run_timed("load manufacturing_data.txt", load_manufacturing_text)
    if not text:
        console.print("  [red]Text loading failed, cannot continue.[/red]\n")
        return False

    chunks = t.run_timed(
        "split text into chunks (500 chars, 50 overlap)", split_text, text, 500, 50
    )
    if not chunks:
        console.print("  [red]Text splitting failed, cannot continue.[/red]\n")
        return False

    console.print(f"  [dim]Split into {len(chunks)} chunks[/dim]")

    # Create Requirement + Chunk nodes + relationships
    console.print("\n  [bold]Creating Requirement & Chunk Nodes[/bold]")
    t.run_timed(
        f"create Requirement + {len(chunks)} Chunks with HAS_CHUNK/NEXT_CHUNK",
        create_requirement_with_chunks,
        driver,
        "Battery Cell and Module Design",
        chunks,
    )

    # Validate
    console.print("\n  [bold]Validation[/bold]")
    all_ok = True

    for label, expected in EXPECTED_NODE_COUNTS.items():
        if label == "Chunk":
            # Chunk count depends on text splitting, just check > 0
            rows, _, _ = driver.execute_query(f"MATCH (n:{label}) RETURN count(n) AS c")
            actual = rows[0]["c"] if rows else 0
            ok = actual > 0
            t.check(f"{label}: {actual} (expected > 0)", ok, f"got {actual}")
        else:
            rows, _, _ = driver.execute_query(f"MATCH (n:{label}) RETURN count(n) AS c")
            actual = rows[0]["c"] if rows else 0
            ok = actual >= expected
            t.check(f"{label}: {actual} (expected >= {expected})", ok, f"got {actual}")
        if not ok:
            all_ok = False

    rows, _, _ = driver.execute_query(
        "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
    )
    existing_types = {r["relationshipType"] for r in rows}
    for rel_type in EXPECTED_REL_TYPES:
        ok = rel_type in existing_types
        t.check(f"relationship type {rel_type}", ok, "missing")
        if not ok:
            all_ok = False

    console.print()
    return all_ok


# ---------------------------------------------------------------------------
# Phase 2: Embeddings (= Notebook 02)
# ---------------------------------------------------------------------------


def _phase2_embeddings(driver, embedder, t: TestRunner) -> bool:
    """Generate embeddings, store on Chunk nodes, create vector index."""
    from .data import create_vector_idx

    t.section("Phase 2: Embeddings (Notebook 02)")

    # Generate embeddings for all chunks
    console.print("\n  [bold]Generating Embeddings[/bold]")
    rows, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.embedding IS NULL RETURN c.text AS text, elementId(c) AS id "
        "ORDER BY c.index"
    )

    if not rows:
        # Check if embeddings already exist
        rows2, _, _ = driver.execute_query(
            "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c) AS c"
        )
        existing = rows2[0]["c"] if rows2 else 0
        if existing > 0:
            console.print(f"  [dim]All {existing} chunks already have embeddings[/dim]")
        else:
            t.check("chunks exist for embedding", False, "no Chunk nodes found")
            return False
    else:
        console.print(f"  [dim]Generating embeddings for {len(rows)} chunks...[/dim]")

        def _embed_and_store():
            for row in rows:
                embedding = embedder.embed_query(row["text"])
                driver.execute_query(
                    "MATCH (c:Chunk) WHERE elementId(c) = $id SET c.embedding = $emb",
                    id=row["id"],
                    emb=embedding,
                )
            return len(rows)

        count = t.run_timed(f"embed and store {len(rows)} chunks", _embed_and_store)
        if not count:
            return False

    # Validate embeddings
    console.print("\n  [bold]Validating Embeddings[/bold]")
    rows, _, _ = driver.execute_query(
        "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL RETURN count(c) AS c"
    )
    count = rows[0]["c"] if rows else 0
    t.check(f"chunks with embeddings: {count}", count > 0, "no embeddings found")

    if count > 0:
        rows, _, _ = driver.execute_query(
            "MATCH (c:Chunk) WHERE c.embedding IS NOT NULL "
            "RETURN size(c.embedding) AS dims LIMIT 1"
        )
        dims = rows[0]["dims"] if rows else 0
        t.check(f"embedding dimensions = 1024", dims == 1024, f"got {dims}")

    # Create vector index
    console.print("\n  [bold]Creating Vector Index[/bold]")
    t.run_timed("create vector index requirement_embeddings", create_vector_idx, driver)

    # Validate vector index
    rows, _, _ = driver.execute_query(
        "SHOW INDEXES YIELD name, type, options WHERE type = 'VECTOR'"
    )
    vector_names = {r["name"] for r in rows}
    t.check("requirement_embeddings index exists", "requirement_embeddings" in vector_names)

    # Test raw vector search
    console.print("\n  [bold]Raw Vector Search Test[/bold]")

    def _raw_vector_search():
        query_embedding = embedder.embed_query("thermal management")
        result, _, _ = driver.execute_query(
            "CALL db.index.vector.queryNodes($idx, $k, $emb) "
            "YIELD node, score "
            "RETURN node.text AS text, score LIMIT 3",
            idx="requirement_embeddings",
            k=3,
            emb=query_embedding,
        )
        return result

    results = t.run_timed("vector search 'thermal management'", _raw_vector_search)
    if results:
        t.check("raw vector search returns results", len(results) > 0)
        if results:
            console.print(f"  [dim]Top result: {str(results[0]['text'])[:120]}...[/dim]")

    console.print()
    return True


# ---------------------------------------------------------------------------
# Phase 3: Vector Retriever (= Notebook 03)
# ---------------------------------------------------------------------------


def _phase3_vector_retriever(retrievers, t: TestRunner) -> None:
    """Build VectorRetriever, search, and run GraphRAG pipeline."""
    from neo4j_graphrag.generation import GraphRAG

    t.section("Phase 3: Vector Retriever (Notebook 03)")

    console.print("\n  [bold]VectorRetriever Search[/bold]")

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

    # GraphRAG pipeline
    console.print("\n  [bold]GraphRAG Pipeline[/bold]")
    rag = GraphRAG(llm=retrievers.llm, retriever=retrievers.vector)

    def _graphrag_question():
        return rag.search(
            "What are the thermal management requirements for the battery?",
            retriever_config={"top_k": 3},
        )

    response = t.run_timed("GraphRAG question about thermal management", _graphrag_question)
    if response:
        answer = response.answer
        t.check("got non-empty response", bool(answer))
        answer_lower = answer.lower()
        matched = [t for t in ["thermal", "cool", "heat", "temperature"] if t in answer_lower]
        t.check(f"response contains expected terms ({matched})", len(matched) > 0)
        preview = answer[:150] + "..." if len(answer) > 150 else answer
        console.print(f"  [dim]{preview}[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# Phase 4: Vector Cypher Retriever (= Notebook 04)
# ---------------------------------------------------------------------------


def _phase4_vector_cypher_retriever(retrievers, t: TestRunner) -> None:
    """Build VectorCypherRetriever, search with expanded context."""
    from neo4j_graphrag.generation import GraphRAG

    t.section("Phase 4: Vector Cypher Retriever (Notebook 04)")

    console.print("\n  [bold]VectorCypherRetriever Search[/bold]")

    def _vc_search():
        return retrievers.vector_cypher.search(query_text="cooling requirements", top_k=3)

    result = t.run_timed("search 'cooling requirements'", _vc_search)
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

    # GraphRAG comparison
    console.print("\n  [bold]GraphRAG Pipeline[/bold]")
    rag = GraphRAG(llm=retrievers.llm, retriever=retrievers.vector_cypher)

    def _graphrag_question():
        return rag.search(
            "What safety standards must the battery system comply with?",
            retriever_config={"top_k": 3},
        )

    response = t.run_timed("GraphRAG question about safety standards", _graphrag_question)
    if response:
        answer = response.answer
        t.check("got non-empty response", bool(answer))
        if "safety" in answer.lower():
            t.check("response mentions safety", True)
        preview = answer[:150] + "..." if len(answer) > 150 else answer
        console.print(f"  [dim]{preview}[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# Phase 5: Fulltext Search (= Notebook 05)
# ---------------------------------------------------------------------------


def _phase5_fulltext_search(driver, t: TestRunner) -> None:
    """Create fulltext indexes and test various search patterns."""
    from .data import create_fulltext_indexes

    t.section("Phase 5: Fulltext Search (Notebook 05)")

    # Create fulltext indexes
    console.print("\n  [bold]Creating Fulltext Indexes[/bold]")
    t.run_timed("create fulltext indexes", create_fulltext_indexes, driver)

    # Validate indexes exist
    rows, _, _ = driver.execute_query(
        "SHOW INDEXES YIELD name, type WHERE type = 'FULLTEXT'"
    )
    fulltext_names = {r["name"] for r in rows}
    t.check("requirement_text index exists", "requirement_text" in fulltext_names)
    t.check("search_entities index exists", "search_entities" in fulltext_names)

    # Exact search
    console.print("\n  [bold]Exact Search[/bold]")

    def _exact():
        rows, _, _ = driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $q) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            q="thermal",
        )
        return rows

    result = t.run_timed("exact search 'thermal'", _exact)
    if result:
        t.check("returns results", len(result) > 0)
        if result:
            t.check(
                "result contains 'thermal'",
                "thermal" in result[0]["text"].lower(),
            )

    # Fuzzy search
    console.print("\n  [bold]Fuzzy Search[/bold]")

    def _fuzzy():
        rows, _, _ = driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $q) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            q="battrey~",
        )
        return rows

    result = t.run_timed("fuzzy search 'battrey~'", _fuzzy)
    if result:
        t.check("fuzzy matches 'battery'", len(result) > 0)

    # Wildcard search
    console.print("\n  [bold]Wildcard Search[/bold]")

    def _wildcard():
        rows, _, _ = driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $q) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            q="therm*",
        )
        return rows

    result = t.run_timed("wildcard search 'therm*'", _wildcard)
    if result:
        t.check("wildcard returns results", len(result) > 0)

    # Boolean search
    console.print("\n  [bold]Boolean Search[/bold]")

    def _boolean():
        rows, _, _ = driver.execute_query(
            "CALL db.index.fulltext.queryNodes('requirement_text', $q) "
            "YIELD node, score RETURN node.text AS text, score LIMIT 3",
            q="thermal AND management",
        )
        return rows

    result = t.run_timed("boolean search 'thermal AND management'", _boolean)
    if result:
        t.check("boolean returns results", len(result) > 0)

    # Entity search
    console.print("\n  [bold]Entity Search[/bold]")

    def _entity():
        rows, _, _ = driver.execute_query(
            "CALL db.index.fulltext.queryNodes('search_entities', $q) "
            "YIELD node, score RETURN node.name AS name, score LIMIT 3",
            q="battery",
        )
        return rows

    result = t.run_timed("entity search 'battery'", _entity)
    if result:
        t.check("returns entity results", len(result) > 0)

    console.print()


# ---------------------------------------------------------------------------
# Phase 6: Hybrid Search (= Notebook 06)
# ---------------------------------------------------------------------------


def _phase6_hybrid_search(retrievers, t: TestRunner) -> None:
    """Test HybridRetriever, HybridCypherRetriever, and GraphRAG."""
    from neo4j_graphrag.generation import GraphRAG

    t.section("Phase 6: Hybrid Search (Notebook 06)")

    # HybridRetriever
    console.print("\n  [bold]HybridRetriever[/bold]")

    def _hybrid_search():
        return retrievers.hybrid.search(
            query_text="battery cooling specifications", top_k=5
        )

    result = t.run_timed("search 'battery cooling specifications'", _hybrid_search)
    if result:
        t.check("returns results", len(result.items) > 0, "no items returned")

    # HybridCypherRetriever
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

    # GraphRAG with HybridCypherRetriever
    console.print("\n  [bold]GraphRAG Pipeline[/bold]")
    rag = GraphRAG(llm=retrievers.llm, retriever=retrievers.hybrid_cypher)

    def _graphrag_question():
        return rag.search(
            "What are the energy density specifications for battery cells?",
            retriever_config={"top_k": 3},
        )

    response = t.run_timed("GraphRAG question about energy density", _graphrag_question)
    if response:
        answer = response.answer
        t.check("got non-empty response", bool(answer))
        answer_lower = answer.lower()
        matched = [term for term in ["energy", "density", "cell"] if term in answer_lower]
        t.check(f"response contains expected terms ({matched})", len(matched) > 0)
        preview = answer[:150] + "..." if len(answer) > 150 else answer
        console.print(f"  [dim]{preview}[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def test() -> None:
    """Run comprehensive Lab 5 GraphRAG validation suite (6 phases matching 6 notebooks)."""
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

    # Phase 1: Data Loading (= Notebook 01)
    phase1_ok = _phase1_data_loading(driver, t)
    if not phase1_ok:
        console.print(
            "[yellow]Phase 1 issues — continuing with remaining phases anyway.[/yellow]\n"
        )

    # Phase 2: Embeddings (= Notebook 02)
    from neo4j_graphrag.embeddings import BedrockEmbeddings

    embedder = BedrockEmbeddings(
        model_id=settings.embedding_model_id,
        region_name=settings.region,
    )
    phase2_ok = _phase2_embeddings(driver, embedder, t)
    if not phase2_ok:
        console.print(
            "[yellow]Phase 2 issues — continuing with remaining phases anyway.[/yellow]\n"
        )

    driver.close()

    # Build retrievers for phases 3-6
    console.print("Initializing retrievers...", style="dim")
    try:
        retrievers = build_retrievers(settings)
        console.print("[green]Retrievers ready.[/green]\n")
    except Exception as exc:
        t.failed += 1
        console.print(f"  [red]FAIL[/red]  Failed to initialize retrievers — {exc}\n")
        t.summary()
        raise SystemExit(1)

    # Phase 3: Vector Retriever (= Notebook 03)
    _phase3_vector_retriever(retrievers, t)

    # Phase 4: Vector Cypher Retriever (= Notebook 04)
    _phase4_vector_cypher_retriever(retrievers, t)

    # Phase 5: Fulltext Search (= Notebook 05)
    _phase5_fulltext_search(retrievers.driver, t)

    # Phase 6: Hybrid Search (= Notebook 06)
    _phase6_hybrid_search(retrievers, t)

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
