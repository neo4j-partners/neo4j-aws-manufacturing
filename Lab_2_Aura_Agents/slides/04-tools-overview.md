# Agent Tools Overview

## Three Retrieval Patterns

| Tool Type | What It Does | Best For |
|-----------|--------------|----------|
| **Cypher Templates** | Run pre-defined queries | Precise, controlled lookups |
| **Similarity Search** | Find semantically similar content | Exploring topics |
| **Text2Cypher** | Convert questions to Cypher | Flexible ad-hoc queries |

## How the Agent Chooses

The agent reads tool descriptions and matches them to questions:

- "Tell me about HVB_3900" → `get_component_overview` (template)
- "What do requirements say about cooling?" → `search_requirement_content` (similarity)
- "How many defects have high severity?" → `query_database` (Text2Cypher)

## Tool Descriptions Matter

Good descriptions help the agent choose correctly.

---

[← Previous](03-what-is-aura-agent.md) | [Next: Cypher Templates →](05-cypher-templates.md)
