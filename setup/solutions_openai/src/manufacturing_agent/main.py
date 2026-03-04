"""CLI entry point for the manufacturing agent."""

from __future__ import annotations

import json
import sys
import time

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from .config import Settings

app = typer.Typer(
    name="manufacturing-agent",
    help="Interactive manufacturing analyst agent (LangChain + OpenAI + Neo4j).",
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
        self._section_count = 0

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
    """Verify indexes, constraints, node counts, and relationships."""
    from .agent import (
        EXPECTED_CONSTRAINTS,
        EXPECTED_INDEXES,
        EXPECTED_NODE_COUNTS,
        EXPECTED_REL_TYPES,
        EXPECTED_VECTOR_INDEXES,
    )

    t.section("Phase 1: Database Preflight")

    # -- Constraints --
    console.print("\n  [bold]Constraints[/bold]")
    rows, _, _ = driver.execute_query("SHOW CONSTRAINTS")
    constraint_set = set()
    for r in rows:
        for label in (r.get("labelsOrTypes") or []):
            for prop in (r.get("properties") or []):
                constraint_set.add((label, prop))

    all_ok = True
    for label, prop in EXPECTED_CONSTRAINTS:
        ok = (label, prop) in constraint_set
        t.check(f"{label}.{prop}", ok, "missing constraint")
        if not ok:
            all_ok = False

    # -- Property indexes --
    console.print("\n  [bold]Property Indexes[/bold]")
    rows, _, _ = driver.execute_query("SHOW INDEXES WHERE type = 'RANGE'")
    index_set = set()
    for r in rows:
        for label in (r.get("labelsOrTypes") or []):
            for prop in (r.get("properties") or []):
                index_set.add((label, prop))

    for label, prop in EXPECTED_INDEXES:
        ok = (label, prop) in index_set
        t.check(f"{label}.{prop}", ok, "missing index")
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
            t.check(f"{name} dimensions = {expected_dims}", vector_map[name] == expected_dims,
                     f"got {vector_map[name]}")
        else:
            all_ok = False

    # -- Node counts --
    console.print("\n  [bold]Node Counts[/bold]")
    for label, expected in EXPECTED_NODE_COUNTS.items():
        rows, _, _ = driver.execute_query(f"MATCH (n:{label}) RETURN count(n) AS c")
        actual = rows[0]["c"] if rows else 0
        t.check(f"{label}: {actual} (expected >= {expected})", actual >= expected,
                 f"got {actual}")
        if actual < expected:
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

    # -- Embeddings populated --
    console.print("\n  [bold]Embeddings[/bold]")
    for label in ("Requirement", "Defect"):
        rows, _, _ = driver.execute_query(
            f"MATCH (n:{label}) WHERE n.embedding IS NOT NULL RETURN count(n) AS c"
        )
        count = rows[0]["c"] if rows else 0
        t.check(f"{label} nodes with embeddings: {count}", count > 0, "no embeddings found")
        if count > 0:
            # Check dimension
            rows2, _, _ = driver.execute_query(
                f"MATCH (n:{label}) WHERE n.embedding IS NOT NULL "
                f"RETURN size(n.embedding) AS dims LIMIT 1"
            )
            dims = rows2[0]["dims"] if rows2 else 0
            t.check(f"{label} embedding dimensions = 1536", dims == 1536, f"got {dims}")

    console.print()
    return all_ok


# ---------------------------------------------------------------------------
# Phase 2: Direct tool tests (bypass agent LLM routing)
# ---------------------------------------------------------------------------

def _test_tools_direct(tools, t: TestRunner) -> None:
    """Call each tool directly and validate response content."""
    t.section("Phase 2: Direct Tool Tests")

    # -- Tool 1: get_component_overview --
    console.print("\n  [bold]get_component_overview[/bold]")
    result = t.run_timed("invoke HVB_3900", tools.get_component_overview.invoke, "HVB_3900")
    if result:
        data = json.loads(result)
        t.check("returns records", len(data) > 0)
        rec = data[0]
        t.check("component = HVB_3900", rec.get("component") == "HVB_3900")
        t.check("technology_domain = Electric Powertrain",
                 rec.get("technology_domain") == "Electric Powertrain")
        t.check("has requirements", len(rec.get("top_requirements", [])) > 0)

    result2 = t.run_timed("invoke NONEXISTENT", tools.get_component_overview.invoke, "NONEXISTENT_XYZ")
    if result2:
        t.check("returns not-found message", "No component found" in result2)

    # -- Tool 2: get_test_coverage --
    console.print("\n  [bold]get_test_coverage[/bold]")
    result = t.run_timed("invoke HVB_3900", tools.get_test_coverage.invoke, "HVB_3900")
    if result:
        data = json.loads(result)
        t.check("returns requirements", len(data) > 0)
        statuses = {r.get("coverage_status") for r in data}
        t.check("has Covered requirements", "Covered" in statuses)
        t.check("has requirement descriptions",
                 all(r.get("requirement_description") for r in data))

    # -- Tool 3: get_milestone_readiness --
    console.print("\n  [bold]get_milestone_readiness[/bold]")
    result = t.run_timed("invoke m_200", tools.get_milestone_readiness.invoke, "m_200")
    if result:
        data = json.loads(result)
        t.check("returns test sets", len(data) > 0)
        rec = data[0]
        t.check("milestone = m_200", rec.get("milestone") == "m_200")
        t.check("has deadline", rec.get("deadline") is not None)
        t.check("has test_set name", rec.get("test_set") is not None)
        # Check that at least some records have open test cases or effort
        has_effort = any(r.get("test_effort_hours", 0) > 0 for r in data)
        t.check("has effort hours", has_effort)

    # -- Tool 4: search_requirement_content (vector search) --
    console.print("\n  [bold]search_requirement_content (vector search)[/bold]")
    result = t.run_timed(
        "invoke 'thermal management'", tools.search_requirement_content.invoke,
        "thermal management and cooling",
    )
    if result:
        data = json.loads(result)
        t.check("returns 5 results", len(data) == 5)
        # Check semantic relevance — at least one result should mention thermal/cooling/heat
        thermal_terms = {"thermal", "cooling", "heat", "temperature"}
        contents = " ".join(r.get("content", "").lower() for r in data)
        matches = thermal_terms & set(contents.split())
        t.check("results are semantically relevant (thermal/cooling/heat)",
                 len(matches) > 0, f"found terms: {matches or 'none'}")

    result2 = t.run_timed(
        "invoke 'safety monitoring'", tools.search_requirement_content.invoke,
        "safety monitoring",
    )
    if result2:
        data2 = json.loads(result2)
        t.check("returns results for safety query", len(data2) > 0)
        safety_terms = {"safety", "monitoring", "redundant", "shutdown"}
        contents2 = " ".join(r.get("content", "").lower() for r in data2)
        matches2 = safety_terms & set(contents2.split())
        t.check("results are semantically relevant (safety/monitoring)",
                 len(matches2) > 0, f"found terms: {matches2 or 'none'}")

    result3 = t.run_timed(
        "invoke 'energy density'", tools.search_requirement_content.invoke,
        "energy density specifications",
    )
    if result3:
        data3 = json.loads(result3)
        t.check("returns results for energy density query", len(data3) > 0)

    # -- Tool 5: query_database (Text2Cypher) --
    console.print("\n  [bold]query_database (Text2Cypher)[/bold]")
    result = t.run_timed(
        "invoke 'most requirements'", tools.query_database.invoke,
        "Which component has the most requirements?",
    )
    if result:
        t.check("mentions HVB_3900", "HVB_3900" in result or "HVB" in result,
                 f"response: {result[:200]}")

    result2 = t.run_timed(
        "invoke 'high severity defects'", tools.query_database.invoke,
        "How many defects have high severity?",
    )
    if result2:
        t.check("returns a response", len(result2) > 0)

    result3 = t.run_timed(
        "invoke 'battery changes'", tools.query_database.invoke,
        "What changes have been proposed that affect battery requirements?",
    )
    if result3:
        t.check("returns a response", len(result3) > 0)

    console.print()


# ---------------------------------------------------------------------------
# Phase 3: Agent integration (LLM selects tools)
# ---------------------------------------------------------------------------

AGENT_QUESTIONS = [
    (
        "Cypher Template",
        "Tell me about the HVB_3900 component and any defects found",
        ["HVB_3900", "Electric Powertrain"],
    ),
    (
        "Cypher Template",
        "What is the test coverage for the HVB_3900 component?",
        ["Covered", "requirement"],
    ),
    (
        "Cypher Template",
        "What needs to be done to achieve milestone m_200?",
        ["m_200"],
    ),
    (
        "Semantic Search",
        "What do the requirements say about thermal management and cooling?",
        ["thermal", "cool"],
    ),
    (
        "Semantic Search",
        "Find requirements related to safety monitoring",
        ["safety", "monitor"],
    ),
    (
        "Text2Cypher",
        "Which component has the most requirements?",
        ["HVB"],
    ),
]


def _extract_answer(result: dict) -> str:
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            return msg.content
    return ""


def _extract_tool_calls(result: dict) -> list[str]:
    """Extract which tools the agent called."""
    names = []
    for msg in result.get("messages", []):
        if hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                names.append(tc.get("name", ""))
    return names


def _test_agent_integration(agent, t: TestRunner) -> None:
    """Run Lab 2 questions through the full agent and validate responses."""
    t.section("Phase 3: Agent Integration (LLM routing)")

    for i, (category, question, expected_terms) in enumerate(AGENT_QUESTIONS, 1):
        console.print(f"\n  [bold]{i}/{len(AGENT_QUESTIONS)} {category}[/bold]")
        console.print(f"  [blue]Q:[/blue] {question}")

        start = time.monotonic()
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": question}]})
            elapsed = time.monotonic() - start
            t.total_time += elapsed

            answer = _extract_answer(result)
            tool_calls = _extract_tool_calls(result)

            t.check(f"got response ({elapsed:.1f}s)", bool(answer))
            t.check(f"agent used tools: {tool_calls}", len(tool_calls) > 0, "no tools called")

            answer_lower = answer.lower()
            for term in expected_terms:
                t.check(f"response contains '{term}'", term.lower() in answer_lower)

            console.print(f"  [dim]{answer[:150]}...[/dim]" if len(answer) > 150 else f"  [dim]{answer}[/dim]")

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
    """Run comprehensive Lab 2 Aura Agent test suite."""
    from .agent import build_agent, build_tools
    from neo4j import GraphDatabase

    settings = Settings()  # type: ignore[call-arg]
    t = TestRunner()

    console.print(f"\nConnecting to {settings.neo4j_uri}...", style="dim")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )
    driver.verify_connectivity()
    console.print("[green]Connected.[/green]\n")

    # Phase 1: Preflight (uses raw driver only, no OpenAI)
    preflight_ok = _test_preflight(driver, t)
    driver.close()

    if not preflight_ok:
        console.print("[yellow]Preflight issues detected — continuing with tool tests anyway.[/yellow]\n")

    # Phase 2: Direct tool tests
    console.print(f"Initializing tools...", style="dim")
    tools = build_tools(settings)
    console.print("[green]Tools ready.[/green]\n")

    _test_tools_direct(tools, t)
    tools.driver.close()

    # Phase 3: Agent integration
    console.print(f"Initializing agent...", style="dim")
    agent, agent_driver = build_agent(settings)
    console.print("[green]Agent ready.[/green]\n")

    _test_agent_integration(agent, t)
    agent_driver.close()

    # Summary
    t.summary()
    if t.failed:
        raise SystemExit(1)


@app.command()
def chat() -> None:
    """Start an interactive chat session with the manufacturing agent."""
    from .agent import build_agent

    settings = Settings()  # type: ignore[call-arg]

    console.print(f"\nConnecting to {settings.neo4j_uri}...", style="dim")
    try:
        agent, driver = build_agent(settings)
    except Exception as exc:
        console.print(f"[red]Failed to initialize agent: {exc}[/red]")
        sys.exit(1)
    console.print("[green]Agent ready.[/green] Type your question or 'quit' to exit.\n")

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
                result = agent.invoke({"messages": [{"role": "user", "content": question}]})
                answer = _extract_answer(result)

                if answer:
                    console.print()
                    console.print(Markdown(answer))
                    console.print()
                else:
                    console.print("[dim]No response.[/dim]\n")
            except Exception as exc:
                console.print(f"\n[red]Error: {exc}[/red]\n")
    finally:
        driver.close()
        console.print("\n[dim]Goodbye.[/dim]")


if __name__ == "__main__":
    app()
