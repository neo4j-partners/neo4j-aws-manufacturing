# Lab 2: Aura Agents

In this lab, you will build an AI-powered agent using Neo4j Aura Agent. The agent will help users explore manufacturing product development data by combining semantic search, graph traversal, and natural language queries - all without writing any code.

## Prerequisites

- Completed **Lab 0** (Sign In)
- Completed **Lab 1** (Neo4j Aura setup with backup restored)

The pre-built backup you restored in Lab 1 already contains the complete knowledge graph with embeddings, so you can start building agents immediately.

## Step 1: Create the Manufacturing Agent

1. Go to [console.neo4j.io](https://console.neo4j.io)
2. Select **Agents** in the left-hand menu
3. Click on **Create Agent**

![Aura Agents](images/aura_agents.png)

## Step 2: Configure Agent Details

Configure your new agent with the following settings. It is critical that you give your agent a unique name so that it does not conflict with other users' agents in the shared environment. If you have an error try another unique name by adding your initials or a number.:

**Unique Agent Name:** `ryans-manufacturing-analyst`

**Description:** An AI-powered manufacturing analyst that helps users explore product development data, analyze component requirements, investigate defects and test results, and discover traceability relationships across the knowledge graph.

**Prompt Instructions:**
```
You are an expert manufacturing engineering assistant specializing in product development traceability.
You help users understand:
- Product structure across technology domains and components
- Engineering requirements and how they relate to components
- Test coverage, defects, and their severity
- Change proposals and their impact on requirements

Always provide specific examples from the knowledge graph when answering questions.
Ground your responses in the actual data from the manufacturing traceability graph.
```

**Target Instance:** Select your Neo4j Aura instance created in Lab 1.

**External Available from an Endpoint:** Enabled

## Step 3: Add Cypher Template Tools

Click **Add Tool** and select **Cypher Template** for each of the following tools:

### Tool 1: Get Component Overview

**Tool Name:** `get_component_overview`

**Description:** Get comprehensive overview of a component including its requirements, technology domain, and associated defects.

**Parameters:** `component_name` (string) - The component name to look up (e.g., "HVB_3900", "PDU_1500")

**Cypher Query:**
```cypher
MATCH (comp:Component {name: $component_name})
OPTIONAL MATCH (td:TechnologyDomain)-[:DOMAIN_HAS_COMPONENT]->(comp)
OPTIONAL MATCH (comp)-[:COMPONENT_HAS_REQ]->(req:Requirement)
OPTIONAL MATCH (req)-[:TESTED_WITH]->(ts:TestSet)-[:CONTAINS_TEST_CASE]->(tc:TestCase)-[:DETECTED]->(d:Defect)
WITH comp, td,
     collect(DISTINCT req.name)[0..10] AS requirements,
     collect(DISTINCT d.description)[0..5] AS defects
RETURN
    comp.name AS component,
    comp.description AS description,
    td.name AS technology_domain,
    requirements AS top_requirements,
    defects AS detected_defects
```

![Add Cypher Template Tool](images/agent_tool_component_overview.png)

### Tool 2: Get Test Coverage of a Component

**Tool Name:** `get_test_coverage`

**Description:** Get the test coverage for a component by showing all its requirements and the test sets assigned to each requirement. Returns a table indicating which requirements are covered by tests and which are not.

**Parameters:**
- `component_name` (string) - The component name to check test coverage for (e.g., "HVB_3900", "PDU_1500")

**Cypher Query:**
```cypher
MATCH (comp:Component {name: $component_name})-[:COMPONENT_HAS_REQ]->(req:Requirement)
OPTIONAL MATCH (req)-[:TESTED_WITH]->(ts:TestSet)
RETURN req.name AS requirement,
       req.description AS requirement_description,
       COLLECT(ts.name) AS test_sets,
       CASE WHEN COUNT(ts) > 0 THEN 'Covered' ELSE 'Not Covered' END AS coverage_status
ORDER BY coverage_status DESC, req.name
```

![Get Test Coverage Tool](images/agent_tool_test_coverage.png)

### Tool 3: Get Milestone Readiness

**Tool Name:** `get_milestone_readiness`

**Description:** Get what needs to be done to achieve a milestone. Returns all open test sets required for the milestone, open defects that need to be closed, and the estimated effort in hours.

**Parameters:**
- `milestone_id` (string) - The milestone ID to check (e.g., "m_200", "m_300", "m_400")

**Cypher Query:**
```cypher
MATCH (m:Milestone {milestone_id: $milestone_id})-[:REQUIRES_ML]->(ml:MaturityLevel)-[:REQUIRES_FLAWLESS_TEST_SET]->(ts:TestSet)
OPTIONAL MATCH (ts)-[:CONTAINS_TEST_CASE]->(tc:TestCase)
WHERE tc.status IN ['Planned', 'In Progress', 'Failed']
OPTIONAL MATCH (d:Defect)-[:DETECTED]->(tc2:TestCase)<-[:CONTAINS_TEST_CASE]-(ts)
WHERE d.status IN ['New', 'In Progress']
WITH m, ts, 
     COLLECT(DISTINCT {name: tc.name, status: tc.status, effort_hours: tc.duration_hours}) AS open_test_cases,
     COLLECT(DISTINCT {defect_id: d.defect_id, description: d.description, severity: d.severity, status: d.status}) AS open_defects
RETURN 
    m.milestone_id AS milestone,
    m.deadline AS deadline,
    ts.name AS test_set,
    [t IN open_test_cases WHERE t.name IS NOT NULL] AS open_test_cases,
    REDUCE(s = 0.0, t IN open_test_cases | s + COALESCE(t.effort_hours, 0.0)) AS test_effort_hours,
    [d IN open_defects WHERE d.defect_id IS NOT NULL] AS open_defects
ORDER BY ts.name
```

![Get Milestone Readiness Tool](images/agent_tool_milestone_readiness.png)

## Step 4: Add Similarity Search Tool

Click **Add Tool** and select **Similarity Search** to configure a semantic search tool using the existing vector index:

**Tool Name:** `search_requirement_content`

**Description:** Search manufacturing requirement descriptions semantically to find relevant passages about specific topics, specifications, or engineering standards.

**Configuration:**
- **Embedding provider:** `openai`
- **Embedding model:** `text-embedding-ada-002`
- **Vector Index:** `requirementEmbeddings`
- **Top K:** 5

![Similarity Search Tool](images/similarity_search_tool.png)

## Step 5: Add Text2Cypher Tool
A **Text2Cypher** tool is already provided by default. It enables natural language to Cypher translation. Change the name and description as follows:

**Tool Name:** `query_database`

**Description:** Query the manufacturing knowledge graph using natural language. This tool translates user questions into Cypher queries to retrieve precise data about products, their components, engineering requirements, test cases, defects, and change proposals. Use this for ad-hoc questions that require flexible data exploration beyond the pre-defined Cypher templates.

![Text2Cypher Tool](images/text2cypher_tool.png)

## Step 6: Test the Agent

Test your agent with the sample questions below. After each test, observe:
1. Which tool the agent selected and why
2. The context retrieved from the knowledge graph
3. How the agent synthesized the response
4. Tool explanations showing the reasoning process

### Cypher Template Questions

Try asking: **"Tell me about the HVB_3900 component and any defects found"**

The agent recognizes this matches the `get_component_overview` template and executes the pre-defined Cypher query with "HVB_3900" as the parameter. We can see the agent's reasoning for selecting the `get_component_overview` tool and how it synthesized the response into a readable format:

![Component Query Agent](images/query_get_component_overview_1.png)
![Component Agent Reasoning](images/query_get_component_overview_2.png)

Other Cypher template questions to try:
- "What is the test coverage for the HVB_3900 component?" - Uses the `get_test_coverage` template to show requirements and their assigned test sets.
- "What needs to be done to achieve milestone m_200?" - Uses the `get_milestone_readiness` template to show open test sets, defects, and effort estimates.

### Semantic Search Questions

Try asking: **"What do the requirements say about thermal management and cooling?"**

The agent uses the similarity search tool to find semantically relevant passages from requirement descriptions, then synthesizes insights about thermal management specifications.

![Thermal Management Agent Response](images/query_semantic_search.png)

Other semantic search questions to try:
- "Find requirements related to safety monitoring" - Searches for passages discussing safety standards and monitoring systems.
- "What specifications exist for energy density?" - Finds relevant energy and battery performance requirements.

### Text2Cypher Questions

Try asking: **"Which component has the most requirements?"**

The agent translates this natural language question into a Cypher query.

![Component Requirements](images/query_text2cypher.png)

Other Text2Cypher questions to try:
- "How many defects have high severity?" - Generates a query to count Defect nodes filtered by severity.
- "What changes have been proposed that affect battery requirements?" - Creates a query to find Change nodes connected to requirements.

## Step 7: (Optional) Use the Aura Agent in your application

Deploy your agent to a production endpoint:
1. Enable external access
2. Copy the authenticated API endpoint
3. Use the endpoint in your applications

## Summary

You have now built an Aura Agent that combines three powerful retrieval patterns:

| Tool Type | Purpose | Best For |
|-----------|---------|----------|
| **Cypher Templates** | Controlled, precise queries | Specific lookups, comparisons |
| **Similarity Search** | Semantic retrieval | Finding relevant content by meaning |
| **Text2Cypher** | Flexible natural language | Ad-hoc questions about the data |

These same patterns are implemented programmatically in Lab 5 (GraphRAG) and Lab 6 (MCP) using Python.

## Next Steps

**This completes Part 1 - No-Code Getting Started.**

To continue with the coding labs, proceed to **Part 2 - Introduction to Agents and GraphRAG with Neo4j**:

[Lab 4 - Intro to Bedrock and Agents](../Lab_4_Intro_to_Bedrock_and_Agents) - Set up your development environment in Amazon SageMaker and learn how AI agents work with LangGraph.