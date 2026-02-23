# Expanded Context Pattern

## The Problem

When you find a relevant chunk, it may be mid-sentence or mid-thought:

```
Chunk 2: "...thermal management system must maintain temperatures..."
```

## The Solution

Traverse `NEXT_CHUNK` to get surrounding context:

```
[Chunk 1: Setup]  →  [Chunk 2: Matched]  →  [Chunk 3: Details]
```

Concatenated, this gives the LLM complete context.

## Why This Matters

Consider: "What are the cooling requirements for the battery?"

- **Matched chunk**: Mentions specific thermal specifications
- **Previous chunk**: Setup and context about the component
- **Next chunk**: Additional specifications and compliance details

The LLM gets **three times the context** for better answers.

---

[← Previous](13-vector-cypher.md) | [Next: The GraphRAG Class →](15-graphrag-class.md)
