# Traditional RAG Limits

## New Problems Emerge

Traditional RAG helps but introduces new challenges:

- Retrieves **similar** content, not necessarily **relevant** content
- Misses **relationships** between pieces of information
- Can make responses **worse** when context is poor (Context ROT)

## Questions Traditional RAG Can't Answer

| Question | Why It Struggles |
|----------|------------------|
| "Which components have requirements affected by change proposals?" | Requires connecting components to changes via requirements |
| "What defects share the same root component?" | Requires finding shared entities |
| "How many requirements mention thermal management?" | Requires aggregation, not similarity |

## The Core Issue

Traditional RAG treats documents as **isolated blobs**.

It ignores the structure and relationships within your data.

---

[← Previous](05-traditional-rag.md) | [Next: The GraphRAG Solution →](07-graphrag-solution.md)
