"""Sample queries showcasing the Manufacturing Product Development knowledge graph."""

from __future__ import annotations

from neo4j import Driver

_W = 70


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _header(title: str, description: str) -> None:
    print(f"\n{'=' * _W}")
    print(f"  {title}")
    print(f"{'=' * _W}")
    print(f"\n  {description}\n")


def _cypher(query: str) -> None:
    lines = query.strip().splitlines()
    indents = [len(ln) - len(ln.lstrip()) for ln in lines if ln.strip()]
    base = min(indents) if indents else 0
    print("  Cypher:")
    for ln in lines:
        print(f"    {ln[base:]}")
    print()


def _table(headers: list[str], rows: list[list], widths: list[int] | None = None) -> None:
    if not rows:
        print("  (no results)\n")
        return
    if widths is None:
        widths = []
        for i, h in enumerate(headers):
            col_max = len(h)
            for row in rows:
                col_max = max(col_max, len(str(row[i] if i < len(row) else "")))
            widths.append(min(col_max + 1, 50))
    print("  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "  ".join("\u2500" * w for w in widths))
    for row in rows:
        cells = []
        for val, w in zip(row, widths):
            s = str(val) if val is not None else "\u2014"
            if len(s) > w:
                s = s[: w - 1] + "\u2026"
            cells.append(s.ljust(w))
        print("  " + "  ".join(cells))
    print()


def _val(v, max_len: int = 0) -> str:
    s = str(v) if v is not None else "\u2014"
    if max_len and len(s) > max_len:
        s = s[: max_len - 1] + "\u2026"
    return s


# ---------------------------------------------------------------------------
# 1. Product overview
# ---------------------------------------------------------------------------

_PRODUCT_Q = """\
MATCH (p:Product)-[:PRODUCT_HAS_DOMAIN]->(td:TechnologyDomain)
OPTIONAL MATCH (td)-[:DOMAIN_HAS_COMPONENT]->(c:Component)
WITH p, td, count(DISTINCT c) AS components
WITH p, collect({domain: td.name, components: components}) AS domains
RETURN p.name AS product, p.description AS description, domains"""


def _product_overview(driver: Driver) -> None:
    _header(
        "1. Product Overview",
        "Product with its Technology Domains and Component counts.",
    )
    _cypher(_PRODUCT_Q)
    rows, _, _ = driver.execute_query(_PRODUCT_Q)
    if not rows:
        print("  (no results)\n")
        return
    for r in rows:
        print(f"  Product: {r['product']} ({r['description']})")
        for d in r["domains"]:
            print(f"    \u251c\u2500\u2500 {d['domain']} ({d['components']} components)")
    print()


# ---------------------------------------------------------------------------
# 2. Requirement traceability
# ---------------------------------------------------------------------------

_TRACE_Q = """\
MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(r:Requirement)
OPTIONAL MATCH (r)-[:TESTED_WITH]->(ts:TestSet)
OPTIONAL MATCH (ts)-[:CONTAINS_TEST_CASE]->(tc:TestCase)
OPTIONAL MATCH (tc)-[:DETECTED]->(d:Defect)
WITH c.name AS component, r.name AS requirement, r.type AS type,
     count(DISTINCT ts) AS test_sets, count(DISTINCT tc) AS test_cases,
     count(DISTINCT d) AS defects
RETURN component, requirement, type, test_sets, test_cases, defects
ORDER BY defects DESC, component NULLS LAST, requirement NULLS LAST
LIMIT $limit"""


def _requirement_traceability(driver: Driver, limit: int) -> None:
    _header(
        "2. Requirement Traceability",
        "Requirements traced from Component through TestSets, TestCases, to Defects.",
    )
    _cypher(_TRACE_Q)
    rows, _, _ = driver.execute_query(_TRACE_Q, limit=limit)
    _table(
        ["Component", "Requirement", "Type", "TestSets", "TestCases", "Defects"],
        [[r["component"], _val(r["requirement"], 25), r["type"],
          r["test_sets"], r["test_cases"], r["defects"]] for r in rows],
    )


# ---------------------------------------------------------------------------
# 3. Change impact analysis
# ---------------------------------------------------------------------------

_CHANGE_Q = """\
MATCH (ch:Change)-[:CHANGE_AFFECTS_REQ]->(r:Requirement)
OPTIONAL MATCH (r)-[:TESTED_WITH]->(ts:TestSet)
WITH ch, r, collect(DISTINCT ts.name) AS affected_test_sets
RETURN ch.change_proposal_id AS change_id,
       ch.criticality AS criticality,
       ch.status AS status,
       r.name AS requirement,
       affected_test_sets
ORDER BY ch.change_proposal_id
LIMIT $limit"""


def _change_impact(driver: Driver, limit: int) -> None:
    _header(
        "3. Change Impact Analysis",
        "Change proposals with the requirements and test sets they affect.",
    )
    _cypher(_CHANGE_Q)
    rows, _, _ = driver.execute_query(_CHANGE_Q, limit=limit)
    for r in rows:
        tests = ", ".join(r["affected_test_sets"]) if r["affected_test_sets"] else "(none)"
        print(f"  {r['change_id']} [{r['criticality']}/{r['status']}]")
        print(f"    Requirement: {_val(r['requirement'], 50)}")
        print(f"    Test Sets:   {tests}")
    print()


# ---------------------------------------------------------------------------
# 4. Milestone timeline
# ---------------------------------------------------------------------------

_MILESTONE_Q = """\
MATCH (m:Milestone)
WHERE m.deadline IS NOT NULL
OPTIONAL MATCH (r:Requirement)-[:REQUIRES_ML]->(m)
WITH m, count(r) AS requirements
OPTIONAL MATCH (m)-[:NEXT]->(next:Milestone)
RETURN m.milestone_id AS milestone, m.deadline AS deadline,
       requirements, next.milestone_id AS next_milestone
ORDER BY m.deadline"""


def _milestone_timeline(driver: Driver) -> None:
    _header(
        "4. Milestone Timeline",
        "Milestones in order with requirement counts and NEXT chain.",
    )
    _cypher(_MILESTONE_Q)
    rows, _, _ = driver.execute_query(_MILESTONE_Q)
    _table(
        ["Milestone", "Deadline", "Requirements", "Next"],
        [[r["milestone"], r["deadline"], r["requirements"],
          _val(r["next_milestone"])] for r in rows],
    )


# ---------------------------------------------------------------------------
# 5. Defect summary
# ---------------------------------------------------------------------------

_DEFECT_Q = """\
MATCH (tc:TestCase)-[:DETECTED]->(d:Defect)
OPTIONAL MATCH (ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc)
OPTIONAL MATCH (r:Requirement)-[:TESTED_WITH]->(ts)
OPTIONAL MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(r)
RETURN d.defect_id AS defect_id, d.description AS description,
       d.severity AS severity, d.status AS status,
       collect(DISTINCT c.name) AS components
ORDER BY d.severity, d.defect_id
LIMIT $limit"""


def _defect_summary(driver: Driver, limit: int) -> None:
    _header(
        "5. Defect Summary",
        "Defects traced back through TestCase \u2192 TestSet \u2192 Requirement \u2192 Component.",
    )
    _cypher(_DEFECT_Q)
    rows, _, _ = driver.execute_query(_DEFECT_Q, limit=limit)
    for r in rows:
        comps = ", ".join(r["components"]) if r["components"] else "(unknown)"
        print(f"  {r['defect_id']} [{r['severity']}/{r['status']}]")
        print(f"    {_val(r['description'], 60)}")
        print(f"    Components: {comps}")
    print()


# ---------------------------------------------------------------------------
# 6. Test coverage
# ---------------------------------------------------------------------------

_COVERAGE_Q = """\
MATCH (r:Requirement)
OPTIONAL MATCH (r)-[:TESTED_WITH]->(ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc:TestCase)
WITH r,
     count(DISTINCT tc) AS total_cases,
     count(DISTINCT CASE WHEN tc.status = 'Passed' THEN tc END) AS passed,
     count(DISTINCT CASE WHEN tc.status = 'Failed' THEN tc END) AS failed,
     count(DISTINCT CASE WHEN tc.status = 'Planned' THEN tc END) AS planned
RETURN r.requirement_id AS req_id, r.name AS requirement,
       total_cases, passed, failed, planned
ORDER BY failed DESC, planned DESC, r.requirement_id
LIMIT $limit"""


def _test_coverage(driver: Driver, limit: int) -> None:
    _header(
        "6. Test Coverage",
        "Requirements with their test case counts by status.",
    )
    _cypher(_COVERAGE_Q)
    rows, _, _ = driver.execute_query(_COVERAGE_Q, limit=limit)
    _table(
        ["Req ID", "Requirement", "Total", "Passed", "Failed", "Planned"],
        [[r["req_id"], _val(r["requirement"], 25), r["total_cases"],
          r["passed"], r["failed"], r["planned"]] for r in rows],
    )


# ---------------------------------------------------------------------------
# 7. Semantic search: Requirements
# ---------------------------------------------------------------------------

_REQ_VECTOR_Q = """\
MATCH (seed:Requirement)
WHERE seed.embedding IS NOT NULL
WITH seed, rand() AS r ORDER BY r LIMIT 1
CALL db.index.vector.queryNodes(
    'requirementEmbeddings', $top_k, seed.embedding
) YIELD node, score
WHERE node <> seed
WITH seed, node, score ORDER BY score DESC LIMIT $limit
RETURN seed.name AS seed_name,
       substring(seed.description, 0, 80) AS seed_desc,
       score AS similarity,
       node.name AS match_name,
       substring(node.description, 0, 80) AS match_desc"""


def _vector_requirements(driver: Driver, limit: int) -> None:
    _header(
        "7. Semantic Search: Requirements",
        "Picks a random requirement and finds the most similar ones using\n"
        "  the vector index (reuses stored embeddings \u2014 no API key needed).",
    )
    _cypher(_REQ_VECTOR_Q)
    try:
        rows, _, _ = driver.execute_query(_REQ_VECTOR_Q, limit=limit, top_k=limit + 1)
    except Exception:
        print("  (vector index not available \u2014 run 'embed' first)\n")
        return
    if not rows:
        print("  (no requirements with embeddings \u2014 run 'embed' first)\n")
        return
    print(f"  Seed: \"{rows[0]['seed_name']}\"")
    print(f"        {rows[0]['seed_desc']}\u2026\n")
    print(f"  {'Score':<8}  Similar requirement")
    print(f"  {'\u2500' * 8}  {'\u2500' * 56}")
    for r in rows:
        print(f"  {r['similarity']:.4f}    {r['match_name']}: {_val(r['match_desc'], 45)}")
    print()


# ---------------------------------------------------------------------------
# 8. Semantic search: Defects
# ---------------------------------------------------------------------------

_DEFECT_VECTOR_Q = """\
MATCH (seed:Defect)
WHERE seed.embedding IS NOT NULL
WITH seed, rand() AS r ORDER BY r LIMIT 1
CALL db.index.vector.queryNodes(
    'defectEmbeddings', $top_k, seed.embedding
) YIELD node, score
WHERE node <> seed
WITH seed, node, score ORDER BY score DESC LIMIT $limit
RETURN seed.defect_id AS seed_id,
       seed.description AS seed_desc,
       score AS similarity,
       node.defect_id AS match_id,
       node.description AS match_desc"""


def _vector_defects(driver: Driver, limit: int) -> None:
    _header(
        "8. Semantic Search: Defects",
        "Picks a random defect and finds the most similar ones using\n"
        "  the vector index (reuses stored embeddings \u2014 no API key needed).",
    )
    _cypher(_DEFECT_VECTOR_Q)
    try:
        rows, _, _ = driver.execute_query(_DEFECT_VECTOR_Q, limit=limit, top_k=limit + 1)
    except Exception:
        print("  (vector index not available \u2014 run 'embed' first)\n")
        return
    if not rows:
        print("  (no defects with embeddings \u2014 run 'embed' first)\n")
        return
    print(f"  Seed: {rows[0]['seed_id']} \u2014 \"{rows[0]['seed_desc']}\"\n")
    print(f"  {'Score':<8}  Similar defect")
    print(f"  {'\u2500' * 8}  {'\u2500' * 56}")
    for r in rows:
        print(f"  {r['similarity']:.4f}    {r['match_id']}: {_val(r['match_desc'], 50)}")
    print()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_all_samples(driver: Driver, sample_size: int = 10) -> None:
    """Run all sample queries with formatted output."""
    print(f"\n{'#' * _W}")
    print("  Manufacturing Product Development \u2014 Sample Queries")
    print(f"{'#' * _W}")
    print(f"\n  Sample size: {sample_size} rows per section\n")

    _product_overview(driver)
    _requirement_traceability(driver, sample_size)
    _change_impact(driver, sample_size)
    _milestone_timeline(driver)
    _defect_summary(driver, sample_size)
    _test_coverage(driver, sample_size)
    _vector_requirements(driver, sample_size)
    _vector_defects(driver, sample_size)

    print(f"{'#' * _W}")
    print("  All samples complete.")
    print(f"{'#' * _W}\n")
