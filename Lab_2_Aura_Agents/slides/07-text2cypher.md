# Text2Cypher Tool

## Natural Language to Database Queries

Text2Cypher uses an LLM to convert questions into Cypher:

```
"Which component has the most requirements?"
    ↓
MATCH (comp:Component)-[:COMPONENT_HAS_REQ]->(req:Requirement)
RETURN comp.name, count(req) AS reqCount
ORDER BY reqCount DESC
LIMIT 1
```

## When to Use

| Question Pattern | Example |
|------------------|---------|
| Counts | "How many defects have high severity?" |
| Lists | "List all components in the database" |
| Comparisons | "Which technology domain has the most components?" |
| Specific facts | "What is the status of defect DEF_001?" |

## Trade-offs

- **Flexible** - Can answer any structured question
- **Less predictable** - LLM may generate different queries
- **Requires good schema understanding** - LLM needs to know your model

---

[← Previous](06-similarity-search.md) | [Next: Lab Steps →](08-lab-steps.md)
