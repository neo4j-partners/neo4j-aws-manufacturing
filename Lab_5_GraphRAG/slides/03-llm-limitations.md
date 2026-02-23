# LLM Limitations

## Three Fundamental Problems

| Problem | Description |
|---------|-------------|
| **Hallucination** | Generates confident but wrong information |
| **Knowledge Cutoff** | No access to recent events or your data |
| **Relationship Blindness** | Can't connect information across documents |

## Hallucination

LLMs generate the most *probable* continuation, not the most *accurate*.

> In 2023, US lawyers were sanctioned for submitting an LLM-generated brief with six fictitious case citations.

## Knowledge Cutoff

Ask about your latest test results or last week's defect report - the LLM may generate a confident (and wrong) response.

## Relationship Blindness

"Which components have requirements affected by open change proposals?"

This requires *reasoning over relationships* - connecting entities across the manufacturing traceability chain.

---

[← Previous](02-genai-promise.md) | [Next: The Solution - Context →](04-solution-context.md)
