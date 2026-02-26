"""Constraint and index definitions for the Manufacturing Product Development graph."""

from __future__ import annotations

from neo4j import Driver

# (label, property) pairs — one uniqueness constraint each.
CONSTRAINTS: list[tuple[str, str]] = [
    ("Product", "product_id"),
    ("TechnologyDomain", "technology_domain_id"),
    ("Component", "component_id"),
    ("Requirement", "requirement_id"),
    ("TestSet", "test_set_id"),
    ("TestCase", "test_case_id"),
    ("Defect", "defect_id"),
    ("Change", "change_proposal_id"),
    ("Milestone", "milestone_id"),
    ("MaturityLevel", "name"),
    ("Resource", "name"),
]

# (label, property) pairs — property indexes for common lookups.
INDEXES: list[tuple[str, str]] = [
    ("Requirement", "type"),
    ("TestCase", "status"),
    ("Defect", "severity"),
    ("Defect", "status"),
    ("Change", "status"),
]

# Vector index definitions: (index_name, label, property, dimensions).
VECTOR_INDEXES: list[tuple[str, str, str, int]] = [
    ("requirementEmbeddings", "Requirement", "embedding", 1536),
    ("defectEmbeddings", "Defect", "embedding", 1536),
]


def create_constraints(driver: Driver) -> None:
    """Create uniqueness constraints (idempotent)."""
    for label, prop in CONSTRAINTS:
        driver.execute_query(
            f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
        print(f"  [OK] Constraint: {label}.{prop}")


def create_indexes(driver: Driver) -> None:
    """Create property indexes (idempotent)."""
    for label, prop in INDEXES:
        index_name = f"idx_{label.lower()}_{prop.lower()}"
        driver.execute_query(
            f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
        )
        print(f"  [OK] Index: {label}.{prop}")


def create_vector_indexes(driver: Driver) -> None:
    """Create vector indexes for embedding similarity search (idempotent)."""
    for name, label, prop, dims in VECTOR_INDEXES:
        driver.execute_query(
            f"CREATE VECTOR INDEX {name} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.{prop}) "
            f"OPTIONS {{indexConfig: {{"
            f"  `vector.dimensions`: {dims},"
            f"  `vector.similarity_function`: 'cosine'"
            f"}}}}"
        )
        print(f"  [OK] Vector index: {name} on {label}.{prop} ({dims} dims)")
