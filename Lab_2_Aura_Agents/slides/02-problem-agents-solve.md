# The Problem Agents Solve

## Users Don't Know Cypher

Your knowledge graph is powerful, but querying it requires Cypher:

```cypher
MATCH (comp:Component)-[:COMPONENT_HAS_REQ]->(req:Requirement)
WHERE comp.name = 'HVB_3900'
RETURN req.name
```

**Most users can't write this.**

## Users Don't Know Retriever Types

You have different retrieval patterns:
- Vector search for semantic content
- Text2Cypher for precise facts
- Graph traversal for relationships

**Users just want to ask questions.**

## The Solution

An agent that **understands questions** and **chooses the right approach** automatically.

---

[← Previous](01-intro.md) | [Next: What is an Aura Agent? →](03-what-is-aura-agent.md)
