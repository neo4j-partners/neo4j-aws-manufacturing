# Manufacturing Traceability Model

## Graph Structure for RAG

```
┌──────────┐   NEXT_CHUNK   ┌──────────┐   NEXT_CHUNK   ┌──────────┐
│  Chunk 1 │───────────────▶│  Chunk 2 │───────────────▶│  Chunk 3 │
└────┬─────┘                └────┬─────┘                └────┬─────┘
     │                           │                           │
     │ HAS_CHUNK                 │ HAS_CHUNK                 │ HAS_CHUNK
     ▼                           ▼                           ▼
┌────────────────────────────────────────────────────────────────────┐
│                         Requirement                                  │
└────────────────────────────────────────────────────────────────────┘
```

## Why This Structure?

| Relationship | Purpose |
|--------------|---------|
| `NEXT_CHUNK` | Retrieve sequential context |
| `HAS_CHUNK` | Track provenance to parent requirement |
| `COMPONENT_HAS_REQ` | Connect to component traceability |

---

[← Previous](07-graphrag-solution.md) | [Next: Chunking Strategies →](09-chunking.md)
