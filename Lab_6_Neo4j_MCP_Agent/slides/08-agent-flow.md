# Agent Flow

## What Happens When You Ask a Question

```
User: "What requirements does the HVB_3900 battery have?"
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Analyzes question, decides to     │
│       first understand the schema       │
│       → Calls: get-schema               │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  MCP Server: Returns schema             │
│  - Nodes: Component, Requirement...     │
│  - Rels: COMPONENT_HAS_REQ, DETECTED... │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Formulates Cypher query           │
│       → Calls: read-cypher              │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  MCP Server: Executes, returns results  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  LLM: Synthesizes human response        │
│  "The HVB_3900 has the following..."    │
└─────────────────────────────────────────┘
```

---

[← Previous](07-schema-matters.md) | [Next: Lab Architecture →](09-architecture.md)
