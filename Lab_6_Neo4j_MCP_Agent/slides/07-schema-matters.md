# Why Schema Matters

## Graph Databases Are Schema-Flexible

Unlike relational databases, graphs don't require predefined tables.

**This means:** The LLM needs to discover what exists.

## What get-schema Reveals

| Component | Examples |
|-----------|----------|
| Node labels | `Product`, `Component`, `Requirement`, `Defect` |
| Relationship types | `COMPONENT_HAS_REQ`, `DETECTED`, `CHANGE_AFFECTS_REQ` |
| Properties | `name`, `description`, `severity` |

## Better Queries

With schema knowledge:

```cypher
-- LLM knows Component has 'name' property
-- LLM knows COMPONENT_HAS_REQ connects Component to Requirement
MATCH (comp:Component {name: 'HVB_3900'})-[:COMPONENT_HAS_REQ]->(req:Requirement)
RETURN req.name
```

Without schema: The LLM guesses and often fails.

---

[← Previous](06-neo4j-mcp.md) | [Next: Agent Flow →](08-agent-flow.md)
