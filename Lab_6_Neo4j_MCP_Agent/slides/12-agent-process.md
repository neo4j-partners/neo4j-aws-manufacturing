# What the Agent Does

## Behind the Scenes

When you ask: **"What requirements does the HVB_3900 have?"**

### Step 1: Schema Discovery
```
Agent → get-schema
← Learns: Component, Requirement, COMPONENT_HAS_REQ
```

### Step 2: Query Generation
```
Agent thinks: "I need to find HVB_3900 and traverse COMPONENT_HAS_REQ"
Generates:
  MATCH (comp:Component)-[:COMPONENT_HAS_REQ]->(req:Requirement)
  WHERE comp.name CONTAINS 'HVB_3900'
  RETURN req.name
```

### Step 3: Execution
```
Agent → read-cypher(query)
← Results: ["Thermal Management", "Energy Density", "Safety Monitoring"]
```

### Step 4: Synthesis
```
"The HVB_3900 component has several key requirements including
thermal management specifications, energy density targets, and
safety monitoring standards."
```

---

[← Previous](11-sample-queries.md) | [Next: Key Takeaways →](13-takeaways.md)
