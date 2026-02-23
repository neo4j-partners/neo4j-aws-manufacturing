# Lab Steps

## Step 1: Create the Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** → **Create Agent**
3. Configure:
   - **Name:** `manufacturing-analyst`
   - **Target Instance:** Your Aura database
   - **External Endpoint:** Enabled

## Step 2: Write Agent Instructions

```
You are an expert manufacturing engineering assistant specializing
in product development traceability. You help users understand:
- Product structure across technology domains and components
- Engineering requirements and test coverage
- Defects, change proposals, and their impact
- Relationships between entities in the manufacturing graph
```

Good instructions guide the agent's tone and focus.

---

[← Previous](07-text2cypher.md) | [Next: Adding Tools →](09-adding-tools.md)
