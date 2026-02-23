"""CSV reading, batched loading, database clearing, and verification."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from neo4j import Driver

BATCH_SIZE = 1000

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def read_csv(data_dir: Path, filename: str) -> list[dict[str, Any]]:
    """Read a CSV file and return a list of row dicts with stripped values.

    Tries utf-8 first, falls back to latin-1 for files with German umlauts.
    """
    path = data_dir / filename
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                reader = csv.DictReader(f)
                rows = []
                for row in reader:
                    rows.append({k.strip(): v.strip() for k, v in row.items() if k is not None})
                return rows
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Cannot decode {filename} with utf-8 or latin-1")


def _run_in_batches(driver: Driver, records: list[dict], query: str) -> None:
    """Execute a Cypher query over records in batches of BATCH_SIZE."""
    total = len(records)
    for i in range(0, total, BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        driver.execute_query(query, batch=batch)
        progress = min(i + BATCH_SIZE, total)
        print(f"  Progress: {progress}/{total} ({100 * progress // total}%)", end="\r")
    print()


# ---------------------------------------------------------------------------
# Node loading
# ---------------------------------------------------------------------------

_NODE_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "Product",
        "products.csv",
        """
        UNWIND $batch AS row
        MERGE (p:Product {product_id: row['product_id']})
        SET p.name = row['Product Name'],
            p.description = row['Description']
        """,
    ),
    (
        "TechnologyDomain",
        "technology_domains.csv",
        """
        UNWIND $batch AS row
        MERGE (td:TechnologyDomain {technology_domain_id: row['technology_domain_id']})
        SET td.name = row['Technology Domain']
        """,
    ),
    (
        "Component",
        "components.csv",
        """
        UNWIND $batch AS row
        MERGE (c:Component {component_id: row['component_id']})
        SET c.name = row['Component'],
            c.description = row['Component Description']
        """,
    ),
    (
        "Requirement",
        "requirements.csv",
        """
        UNWIND $batch AS row
        MERGE (r:Requirement {requirement_id: row['requirement_id']})
        SET r.name = row['Requirement'],
            r.description = row['Description'],
            r.name_de = row['Anforderung'],
            r.description_de = row['Beschreibung'],
            r.vehicle_project = row['Vehicle Project'],
            r.technology_cluster = row['Technology Cluster'],
            r.component = row['Component'],
            r.type = row['Type']
        """,
    ),
    (
        "TestSet",
        "test_sets.csv",
        """
        UNWIND $batch AS row
        MERGE (ts:TestSet {test_set_id: row['test_set_id']})
        SET ts.name = row['Test Set']
        """,
    ),
    (
        "TestCase",
        "test_cases.csv",
        """
        UNWIND $batch AS row
        MERGE (tc:TestCase {test_case_id: row['Test Case ID']})
        SET tc.name = row['Test Case'],
            tc.status = row['Test Status'],
            tc.resources = row['Resources'],
            tc.duration_hours = toFloat(row['Test Duration (hours)']),
            tc.start_date = row['Start Date'],
            tc.end_date = row['End Date'],
            tc.responsibility = row['Responsibility'],
            tc.i_stage = row['I-Stage']
        """,
    ),
    (
        "Defect",
        "defects.csv",
        """
        UNWIND $batch AS row
        MERGE (d:Defect {defect_id: row['defect_id']})
        SET d.description = row['Description'],
            d.severity = row['Severity'],
            d.priority = row['Priority'],
            d.assigned_to = row['Assigned To'],
            d.status = row['Status'],
            d.creation_date = row['Creation Date'],
            d.resolved_date = row['Resolved Date'],
            d.resolution = row['Resolution'],
            d.comments = row['Comments']
        """,
    ),
    (
        "Change",
        "changes.csv",
        """
        UNWIND $batch AS row
        MERGE (ch:Change {change_proposal_id: row['change_proposal_id']})
        SET ch.description = row['Description'],
            ch.criticality = row['Criticality'],
            ch.dev_cost_usd = row['Development Cost in USD'],
            ch.production_cost_usd_per_unit = row['Production Cost in USD per unit'],
            ch.status = row['Status'],
            ch.urgency = row['Urgency'],
            ch.risk = row['Risk']
        """,
    ),
    (
        "Milestone",
        "milestones.csv",
        """
        UNWIND $batch AS row
        MERGE (m:Milestone {milestone_id: row['milestone_id']})
        SET m.deadline = row['Deadline']
        """,
    ),
]

# ---------------------------------------------------------------------------
# Derived node loading (MaturityLevel, Resource from TestCase data)
# ---------------------------------------------------------------------------

_DERIVED_MATURITY_LEVEL = """
MATCH (tc:TestCase)
WHERE tc.i_stage IS NOT NULL AND tc.i_stage <> ''
WITH DISTINCT tc.i_stage AS stage
MERGE (ml:MaturityLevel {name: stage})
RETURN count(ml) AS created
"""

_DERIVED_RESOURCE = """
MATCH (tc:TestCase)
WHERE tc.resources IS NOT NULL AND tc.resources <> ''
WITH DISTINCT tc.resources AS res
MERGE (r:Resource {name: res})
RETURN count(r) AS created
"""

# ---------------------------------------------------------------------------
# Relationship loading
# ---------------------------------------------------------------------------

_REL_DEFINITIONS: list[tuple[str, str, str]] = [
    (
        "PRODUCT_HAS_DOMAIN",
        "product_technology_domains.csv",
        """
        UNWIND $batch AS row
        MATCH (p:Product {product_id: row['product_id']})
        MATCH (td:TechnologyDomain {technology_domain_id: row['technology_domain_id']})
        MERGE (p)-[:PRODUCT_HAS_DOMAIN]->(td)
        """,
    ),
    (
        "DOMAIN_HAS_COMPONENT",
        "technology_domains_components.csv",
        """
        UNWIND $batch AS row
        MATCH (td:TechnologyDomain {technology_domain_id: row['technology_domain_id']})
        MATCH (c:Component {component_id: row['component_id']})
        MERGE (td)-[:DOMAIN_HAS_COMPONENT]->(c)
        """,
    ),
    (
        "COMPONENT_HAS_REQ",
        "components_requirements.csv",
        """
        UNWIND $batch AS row
        MATCH (c:Component {component_id: row['component_id']})
        MATCH (r:Requirement {requirement_id: row['requirement_id']})
        MERGE (c)-[:COMPONENT_HAS_REQ]->(r)
        """,
    ),
    (
        "TESTED_WITH",
        "requirements_test_sets.csv",
        """
        UNWIND $batch AS row
        MATCH (r:Requirement {requirement_id: row['requirement_id']})
        MATCH (ts:TestSet {test_set_id: row['test_set_id']})
        MERGE (r)-[:TESTED_WITH]->(ts)
        """,
    ),
    (
        "CONTAINS_TEST_CASE",
        "test_sets_test_cases.csv",
        """
        UNWIND $batch AS row
        MATCH (ts:TestSet {test_set_id: row['test_set_id']})
        MATCH (tc:TestCase {test_case_id: row['test_case_id']})
        MERGE (ts)-[:CONTAINS_TEST_CASE]->(tc)
        """,
    ),
    (
        "DETECTED",
        "test_case_defect.csv",
        """
        UNWIND $batch AS row
        MATCH (tc:TestCase {test_case_id: row['test_case_id']})
        MATCH (d:Defect {defect_id: row['defect_id']})
        MERGE (tc)-[:DETECTED]->(d)
        """,
    ),
    (
        "CHANGE_AFFECTS_REQ",
        "changes_requirements.csv",
        """
        UNWIND $batch AS row
        MATCH (ch:Change {change_proposal_id: row['change_proposal_id']})
        MATCH (r:Requirement {requirement_id: row['requirement_id']})
        MERGE (ch)-[:CHANGE_AFFECTS_REQ]->(r)
        """,
    ),
    (
        "REQUIRES_ML (Requirement → Milestone)",
        "requirements_test_sets_milestone.csv",
        """
        UNWIND $batch AS row
        MATCH (r:Requirement {requirement_id: row['requirement_id']})
        MATCH (m:Milestone {milestone_id: row['milestone_id']})
        MERGE (r)-[:REQUIRES_ML]->(m)
        """,
    ),
    (
        "REQUIRES_FLAWLESS_TEST_SET (Requirement → TestSet with milestone)",
        "requirements_test_sets_milestone.csv",
        """
        UNWIND $batch AS row
        MATCH (r:Requirement {requirement_id: row['requirement_id']})
        MATCH (ts:TestSet {test_set_id: row['test_set_id']})
        MERGE (r)-[rel:REQUIRES_FLAWLESS_TEST_SET]->(ts)
        SET rel.milestone_id = row['milestone_id']
        """,
    ),
]

# Derived relationships
_TESTCASE_MATURITY = """
MATCH (tc:TestCase)
WHERE tc.i_stage IS NOT NULL AND tc.i_stage <> ''
MATCH (ml:MaturityLevel {name: tc.i_stage})
MERGE (tc)-[:REQUIRES_ML]->(ml)
"""

_TESTCASE_RESOURCE = """
MATCH (tc:TestCase)
WHERE tc.resources IS NOT NULL AND tc.resources <> ''
MATCH (r:Resource {name: tc.resources})
MERGE (tc)-[:REQUIRES]->(r)
"""

# Milestone NEXT chain — sort by milestone_id (m_100, m_200, ...) which is
# already in chronological order. The deadline strings (M/D/YY) don't sort
# correctly as strings.
_MILESTONE_NEXT = """
MATCH (m:Milestone)
WHERE m.milestone_id IS NOT NULL
WITH m ORDER BY m.milestone_id
WITH collect(m) AS milestones
UNWIND range(0, size(milestones)-2) AS i
WITH milestones[i] AS current, milestones[i+1] AS next
MERGE (current)-[:NEXT]->(next)
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_nodes(driver: Driver, data_dir: Path) -> None:
    """Load all node types from CSV files."""
    for label, filename, query in _NODE_DEFINITIONS:
        print(f"Loading {label} nodes...")
        records = read_csv(data_dir, filename)
        _run_in_batches(driver, records, query)
        print(f"  [OK] Loaded {len(records)} {label} nodes.")

    # Derived nodes
    print("Creating MaturityLevel nodes (from TestCase.i_stage)...")
    records, _, _ = driver.execute_query(_DERIVED_MATURITY_LEVEL)
    print(f"  [OK] Created {records[0]['created']} MaturityLevel nodes.")

    print("Creating Resource nodes (from TestCase.resources)...")
    records, _, _ = driver.execute_query(_DERIVED_RESOURCE)
    print(f"  [OK] Created {records[0]['created']} Resource nodes.")


def load_relationships(driver: Driver, data_dir: Path) -> None:
    """Load all relationship types from CSV files and derived relationships."""
    for rel_type, filename, query in _REL_DEFINITIONS:
        print(f"Loading {rel_type} relationships...")
        records = read_csv(data_dir, filename)
        _run_in_batches(driver, records, query)
        print(f"  [OK] Loaded {len(records)} {rel_type} relationships.")

    # Derived relationships
    print("Creating TestCase → MaturityLevel relationships...")
    driver.execute_query(_TESTCASE_MATURITY)
    print("  [OK] Created REQUIRES_ML relationships.")

    print("Creating TestCase → Resource relationships...")
    driver.execute_query(_TESTCASE_RESOURCE)
    print("  [OK] Created REQUIRES relationships.")

    print("Creating Milestone NEXT chain...")
    driver.execute_query(_MILESTONE_NEXT)
    print("  [OK] Created NEXT chain between milestones.")


def clear_database(driver: Driver) -> None:
    """Delete all nodes and relationships in batches."""
    print("Clearing database...")
    deleted_total = 0
    while True:
        records, _, _ = driver.execute_query(
            "MATCH (n) WITH n LIMIT 500 DETACH DELETE n RETURN count(*) AS deleted"
        )
        count = records[0]["deleted"]
        deleted_total += count
        if count > 0:
            print(f"  Deleted {deleted_total} nodes so far...", end="\r")
        if count == 0:
            break
    print(f"\n  [OK] Database cleared ({deleted_total} nodes deleted).")


_NODE_LABELS = [
    "Product", "TechnologyDomain", "Component", "Requirement",
    "TestSet", "TestCase", "Defect", "Change", "Milestone",
    "MaturityLevel", "Resource",
]


def verify(driver: Driver) -> None:
    """Print node counts per label and total relationship count."""
    unions = " UNION ALL ".join(
        f"MATCH (n:{label}) RETURN '{label}' AS label, count(n) AS count"
        for label in _NODE_LABELS
    )
    node_counts, _, _ = driver.execute_query(
        f"CALL () {{ {unions} }} RETURN label, count ORDER BY count DESC"
    )

    print()
    print("=" * 50)
    print("Node Counts:")
    total_nodes = 0
    for row in node_counts:
        if row["count"] > 0:
            print(f"  {row['label']}: {row['count']:,}")
            total_nodes += row["count"]
    print(f"  ---------------------")
    print(f"  Total Nodes: {total_nodes:,}")

    rel_records, _, _ = driver.execute_query(
        "MATCH ()-[r]->() RETURN count(r) AS count"
    )
    rel_count = rel_records[0]["count"]
    print(f"\nTotal Relationships: {rel_count:,}")
    print("=" * 50)
