# Cypher Template Tools

## Controlled, Precise Queries

Cypher templates are pre-defined queries with parameters:

```cypher
MATCH (comp:Component {name: $component_name})
OPTIONAL MATCH (comp)-[:COMPONENT_HAS_REQ]->(req:Requirement)
RETURN comp.name, collect(req.name) AS requirements
```

## Why Use Templates?

| Benefit | Description |
|---------|-------------|
| **Predictable** | Same query every time |
| **Optimized** | You control the query structure |
| **Secure** | No arbitrary query generation |
| **Fast** | No LLM query generation overhead |

## Templates You'll Create

- `get_component_overview` - Component info + requirements + defects
- `find_shared_requirements` - Requirements two components share

---

[← Previous](04-tools-overview.md) | [Next: Similarity Search →](06-similarity-search.md)
