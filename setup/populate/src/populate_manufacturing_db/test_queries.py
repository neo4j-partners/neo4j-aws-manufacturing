"""Test queries demonstrating semantic similarity and hybrid search patterns.

These queries mirror the retriever patterns used in Lab_5_GraphRAG but operate
directly on the whole-description embeddings stored on Requirement and Defect
nodes (no chunking / no Chunk nodes).

Run via:  uv run populate-manufacturing-db test-queries
"""

from __future__ import annotations

import json
import time

import boto3
from neo4j import Driver

from .config import Settings

_W = 70


# ---------------------------------------------------------------------------
# Helpers
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


def _val(v, max_len: int = 0) -> str:
    s = str(v) if v is not None else "\u2014"
    if max_len and len(s) > max_len:
        s = s[: max_len - 1] + "\u2026"
    return s


def _embed_query(client, model_id: str, text: str) -> list[float]:
    """Embed a single query string using Bedrock Titan Embed v2."""
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


# ---------------------------------------------------------------------------
# 1. Pure vector similarity — Requirements
# ---------------------------------------------------------------------------

_VEC_REQ_Q = """\
CALL db.index.vector.queryNodes('requirementEmbeddings', $top_k, $embedding)
YIELD node AS req, score
RETURN req.requirement_id AS req_id,
       req.name AS name,
       req.description AS description,
       score
ORDER BY score DESC"""


def _vector_requirement_search(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "1. Vector Similarity — Requirements",
        f'Find requirements semantically similar to: "{query}"',
    )
    _cypher(_VEC_REQ_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_VEC_REQ_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no results — run 'embed' first)\n")
        return
    print(f"  {'Score':<8}  {'Requirement':<30}  Description")
    print(f"  {'\u2500' * 8}  {'\u2500' * 30}  {'\u2500' * 28}")
    for r in rows:
        print(f"  {r['score']:.4f}    {_val(r['name'], 28):<30}  {_val(r['description'], 40)}")
    print()


# ---------------------------------------------------------------------------
# 2. Pure vector similarity — Defects
# ---------------------------------------------------------------------------

_VEC_DEF_Q = """\
CALL db.index.vector.queryNodes('defectEmbeddings', $top_k, $embedding)
YIELD node AS defect, score
RETURN defect.defect_id AS defect_id,
       defect.description AS description,
       defect.severity AS severity,
       defect.status AS status,
       score
ORDER BY score DESC"""


def _vector_defect_search(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "2. Vector Similarity — Defects",
        f'Find defects semantically similar to: "{query}"',
    )
    _cypher(_VEC_DEF_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_VEC_DEF_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no results — run 'embed' first)\n")
        return
    print(f"  {'Score':<8}  {'Defect':<10}  {'Severity':<10}  Description")
    print(f"  {'\u2500' * 8}  {'\u2500' * 10}  {'\u2500' * 10}  {'\u2500' * 36}")
    for r in rows:
        print(
            f"  {r['score']:.4f}    {r['defect_id']:<10}  {_val(r['severity'], 10):<10}  "
            f"{_val(r['description'], 40)}"
        )
    print()


# ---------------------------------------------------------------------------
# 3. Vector + graph context — Requirement with component traceability
# ---------------------------------------------------------------------------

_VEC_GRAPH_REQ_Q = """\
CALL db.index.vector.queryNodes('requirementEmbeddings', $top_k, $embedding)
YIELD node AS req, score
OPTIONAL MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(req)
OPTIONAL MATCH (req)-[:TESTED_WITH]->(ts:TestSet)
WITH req, score, c,
     count(DISTINCT ts) AS test_sets
RETURN req.requirement_id AS req_id,
       req.name AS name,
       req.description AS description,
       c.name AS component,
       test_sets,
       score
ORDER BY score DESC"""


def _vector_graph_requirement(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "3. Vector + Graph Context — Requirements",
        f'Semantic search with component and test set context.\n  Query: "{query}"',
    )
    _cypher(_VEC_GRAPH_REQ_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_VEC_GRAPH_REQ_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no results)\n")
        return
    for r in rows:
        print(f"  [{r['score']:.4f}] {r['name']} ({r['component']})")
        print(f"           {_val(r['description'], 60)}")
        print(f"           Test sets: {r['test_sets']}")
    print()


# ---------------------------------------------------------------------------
# 4. Vector + graph context — Defect with full traceability chain
# ---------------------------------------------------------------------------

_VEC_GRAPH_DEF_Q = """\
CALL db.index.vector.queryNodes('defectEmbeddings', $top_k, $embedding)
YIELD node AS defect, score
OPTIONAL MATCH (tc:TestCase)-[:DETECTED]->(defect)
OPTIONAL MATCH (ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc)
OPTIONAL MATCH (req:Requirement)-[:TESTED_WITH]->(ts)
OPTIONAL MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(req)
WITH defect, score,
     collect(DISTINCT c.name) AS components,
     collect(DISTINCT req.name) AS requirements,
     collect(DISTINCT tc.name) AS test_cases
RETURN defect.defect_id AS defect_id,
       defect.description AS description,
       defect.severity AS severity,
       defect.status AS status,
       components,
       requirements,
       test_cases,
       score
ORDER BY score DESC"""


def _vector_graph_defect(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "4. Vector + Graph Context — Defect Traceability",
        f'Semantic defect search with full traceability chain.\n  Query: "{query}"',
    )
    _cypher(_VEC_GRAPH_DEF_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_VEC_GRAPH_DEF_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no results)\n")
        return
    for r in rows:
        comps = ", ".join(r["components"]) if r["components"] else "(unknown)"
        reqs = ", ".join(r["requirements"][:3]) if r["requirements"] else "(none)"
        tests = ", ".join(r["test_cases"][:3]) if r["test_cases"] else "(none)"
        print(f"  [{r['score']:.4f}] {r['defect_id']} — {r['description']}")
        print(f"           Severity: {r['severity']}  Status: {r['status']}")
        print(f"           Components: {comps}")
        print(f"           Requirements: {_val(reqs, 60)}")
        print(f"           Test cases: {_val(tests, 60)}")
    print()


# ---------------------------------------------------------------------------
# 5. Cross-domain similarity — find defects related to a requirement query
# ---------------------------------------------------------------------------

_CROSS_Q = """\
CALL db.index.vector.queryNodes('requirementEmbeddings', $top_k, $embedding)
YIELD node AS req, score AS req_score
MATCH (req)<-[:COMPONENT_HAS_REQ]-(c:Component)
MATCH (req)-[:TESTED_WITH]->(ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc:TestCase)
      -[:DETECTED]->(d:Defect)
WITH req, req_score, c,
     collect(DISTINCT {
       defect_id: d.defect_id,
       description: d.description,
       severity: d.severity,
       status: d.status
     }) AS defects
RETURN req.name AS requirement,
       c.name AS component,
       req_score,
       defects
ORDER BY req_score DESC"""


def _cross_domain_search(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "5. Cross-Domain — Requirements → Defects",
        f'Find requirements matching "{query}", then traverse\n'
        "  the graph to surface related defects.",
    )
    _cypher(_CROSS_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_CROSS_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no matching requirements with defects)\n")
        return
    for r in rows:
        print(f"  [{r['req_score']:.4f}] {r['requirement']} ({r['component']})")
        for d in r["defects"]:
            print(f"           \u2514\u2500 {d['defect_id']} [{d['severity']}/{d['status']}] {d['description']}")
    print()


# ---------------------------------------------------------------------------
# 6. Hybrid: vector + keyword filter
# ---------------------------------------------------------------------------

_HYBRID_Q = """\
CALL db.index.vector.queryNodes('requirementEmbeddings', $top_k, $embedding)
YIELD node AS req, score
WHERE req.type = $req_type
OPTIONAL MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(req)
RETURN req.requirement_id AS req_id,
       req.name AS name,
       req.type AS type,
       req.description AS description,
       c.name AS component,
       score
ORDER BY score DESC"""


def _hybrid_type_filter(
    driver: Driver, client, model_id: str, query: str, req_type: str, top_k: int
) -> None:
    _header(
        "6. Hybrid — Vector + Property Filter",
        f'Semantic search filtered to type="{req_type}".\n  Query: "{query}"',
    )
    _cypher(_HYBRID_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(
        _HYBRID_Q, embedding=embedding, top_k=top_k, req_type=req_type
    )
    if not rows:
        print(f"  (no {req_type} requirements match)\n")
        return
    print(f"  {'Score':<8}  {'Type':<6}  {'Component':<12}  {'Requirement':<25}  Description")
    print(f"  {'\u2500' * 8}  {'\u2500' * 6}  {'\u2500' * 12}  {'\u2500' * 25}  {'\u2500' * 20}")
    for r in rows:
        print(
            f"  {r['score']:.4f}    {r['type']:<6}  {_val(r['component'], 12):<12}  "
            f"{_val(r['name'], 25):<25}  {_val(r['description'], 35)}"
        )
    print()


# ---------------------------------------------------------------------------
# 7. Hybrid: vector + severity filter on defects
# ---------------------------------------------------------------------------

_HYBRID_SEV_Q = """\
CALL db.index.vector.queryNodes('defectEmbeddings', $top_k, $embedding)
YIELD node AS defect, score
WHERE defect.severity = $severity
OPTIONAL MATCH (tc:TestCase)-[:DETECTED]->(defect)
OPTIONAL MATCH (ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc)
OPTIONAL MATCH (req:Requirement)-[:TESTED_WITH]->(ts)
RETURN defect.defect_id AS defect_id,
       defect.description AS description,
       defect.severity AS severity,
       defect.status AS status,
       collect(DISTINCT req.name) AS affected_requirements,
       score
ORDER BY score DESC"""


def _hybrid_severity_filter(
    driver: Driver, client, model_id: str, query: str, severity: str, top_k: int
) -> None:
    _header(
        "7. Hybrid — Vector + Severity Filter",
        f'Find {severity}-severity defects matching: "{query}"',
    )
    _cypher(_HYBRID_SEV_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(
        _HYBRID_SEV_Q, embedding=embedding, top_k=top_k, severity=severity
    )
    if not rows:
        print(f"  (no {severity} defects match)\n")
        return
    for r in rows:
        reqs = ", ".join(r["affected_requirements"]) if r["affected_requirements"] else "(none)"
        print(f"  [{r['score']:.4f}] {r['defect_id']} [{r['severity']}/{r['status']}]")
        print(f"           {r['description']}")
        print(f"           Affected: {_val(reqs, 60)}")
    print()


# ---------------------------------------------------------------------------
# 8. Multi-hop graph-enhanced — Change impact via semantic search
# ---------------------------------------------------------------------------

_CHANGE_IMPACT_Q = """\
CALL db.index.vector.queryNodes('requirementEmbeddings', $top_k, $embedding)
YIELD node AS req, score
MATCH (ch:Change)-[:CHANGE_AFFECTS_REQ]->(req)
WITH req, score,
     collect(DISTINCT {
       change_id: ch.change_proposal_id,
       criticality: ch.criticality,
       status: ch.status,
       description: ch.description
     }) AS changes
OPTIONAL MATCH (c:Component)-[:COMPONENT_HAS_REQ]->(req)
RETURN req.name AS requirement,
       c.name AS component,
       score,
       changes
ORDER BY score DESC"""


def _change_impact_search(
    driver: Driver, client, model_id: str, query: str, top_k: int
) -> None:
    _header(
        "8. Multi-Hop — Semantic Search → Change Impact",
        f'Find requirements matching "{query}", then\n'
        "  traverse to active change proposals affecting them.",
    )
    _cypher(_CHANGE_IMPACT_Q)
    embedding = _embed_query(client, model_id, query)
    rows, _, _ = driver.execute_query(_CHANGE_IMPACT_Q, embedding=embedding, top_k=top_k)
    if not rows:
        print("  (no matching requirements with change proposals)\n")
        return
    for r in rows:
        print(f"  [{r['score']:.4f}] {r['requirement']} ({r['component']})")
        for ch in r["changes"]:
            print(
                f"           \u2514\u2500 {ch['change_id']} [{ch['criticality']}/{ch['status']}] "
                f"{_val(ch['description'], 45)}"
            )
    print()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Each test case is a tuple: (function, query_text, extra_kwargs)
_TEST_CASES: list[tuple] = [
    (_vector_requirement_search, "thermal management and battery cooling", {}),
    (_vector_defect_search, "battery temperature exceeding limits", {}),
    (_vector_graph_requirement, "electrical safety and high voltage protection", {}),
    (_vector_graph_defect, "component not meeting design specifications", {}),
    (_cross_domain_search, "electromagnetic compatibility and interference", {}),
    (_hybrid_type_filter, "safety monitoring systems", {"req_type": "HW"}),
    (_hybrid_severity_filter, "insulation and isolation failure", {"severity": "Critical"}),
    (_change_impact_search, "charging system and power delivery", {}),
]


def run_test_queries(driver: Driver, settings: Settings, top_k: int = 5) -> None:
    """Run all test queries with live Bedrock embeddings."""
    client = boto3.client("bedrock-runtime", region_name=settings.region)
    model_id = settings.embedding_model_id

    print(f"\n{'#' * _W}")
    print("  Semantic Similarity & Hybrid Search — Test Queries")
    print(f"{'#' * _W}")
    print(f"\n  Model: {model_id} (region: {settings.region})")
    print(f"  Top-K: {top_k}\n")

    start = time.monotonic()
    passed = 0

    for fn, query, kwargs in _TEST_CASES:
        try:
            fn(driver, client, model_id, query, top_k=top_k, **kwargs)
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {exc}\n")

    elapsed = time.monotonic() - start
    print(f"{'#' * _W}")
    print(f"  {passed}/{len(_TEST_CASES)} test queries completed in {elapsed:.1f}s.")
    print(f"{'#' * _W}\n")
