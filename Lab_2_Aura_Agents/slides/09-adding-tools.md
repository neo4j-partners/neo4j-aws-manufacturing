# Adding Tools

## Step 3: Add Cypher Template Tools

**Tool 1: get_component_overview**
```cypher
MATCH (comp:Component {name: $component_name})
OPTIONAL MATCH (comp)-[:COMPONENT_HAS_REQ]->(req:Requirement)
OPTIONAL MATCH (td:TechnologyDomain)-[:DOMAIN_HAS_COMPONENT]->(comp)
RETURN comp.name, collect(DISTINCT req.name)[0..10] AS requirements,
       td.name AS technology_domain
```

**Tool 2: find_shared_requirements**
```cypher
MATCH (c1:Component {name: $component1})-[:COMPONENT_HAS_REQ]->(r:Requirement)
MATCH (c2:Component {name: $component2})-[:COMPONENT_HAS_REQ]->(r2:Requirement)
RETURN c1.name, size(collect(DISTINCT r)) AS reqs_1,
       c2.name, size(collect(DISTINCT r2)) AS reqs_2
```

## Step 4: Add Similarity Search

- Index: `requirement_embeddings`
- Model: `text-embedding-ada-002`

## Step 5: Add Text2Cypher

For flexible, ad-hoc queries.

---

[← Previous](08-lab-steps.md) | [Next: Testing Your Agent →](10-testing.md)
