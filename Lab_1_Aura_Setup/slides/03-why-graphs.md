# Why Graph Databases?

## The Problem with Relational Databases

Traditional databases struggle with **connected data**:

| Query | Relational Approach | Graph Approach |
|-------|---------------------|----------------|
| "Friends of friends" | Multiple JOINs, slow | Single traversal |
| "What impacts what?" | Complex subqueries | Pattern matching |
| "How are these connected?" | Hard to express | Native relationships |

## Real-World Impact

Questions like:
- "Which components have requirements affected by open change proposals?"
- "What defects are linked to the high-voltage battery?"

These require **traversing relationships** - exactly what graphs do best.

---

[← Previous](02-what-youll-build.md) | [Next: What is Neo4j Aura? →](04-neo4j-aura.md)
