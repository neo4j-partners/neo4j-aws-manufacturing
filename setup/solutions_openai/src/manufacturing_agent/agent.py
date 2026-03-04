"""Agent construction: 5 tools + LangGraph ReAct agent."""

from __future__ import annotations

import json
from dataclasses import dataclass

from langchain_neo4j import GraphCypherQAChain, Neo4jGraph, Neo4jVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from neo4j import Driver, GraphDatabase

from .config import Settings

SYSTEM_PROMPT = """\
You are an expert manufacturing engineering assistant specializing in product development traceability.
You help users understand:
- Product structure across technology domains and components
- Engineering requirements and how they relate to components
- Test coverage, defects, and their severity
- Change proposals and their impact on requirements

Always provide specific examples from the knowledge graph when answering questions.
Ground your responses in the actual data from the manufacturing traceability graph.
"""

# --- Cypher queries (exact copies from Lab 2) ---

COMPONENT_OVERVIEW_CYPHER = """\
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
    defects AS detected_defects"""

TEST_COVERAGE_CYPHER = """\
MATCH (comp:Component {name: $component_name})-[:COMPONENT_HAS_REQ]->(req:Requirement)
OPTIONAL MATCH (req)-[:TESTED_WITH]->(ts:TestSet)
RETURN req.name AS requirement,
       req.description AS requirement_description,
       COLLECT(ts.name) AS test_sets,
       CASE WHEN COUNT(ts) > 0 THEN 'Covered' ELSE 'Not Covered' END AS coverage_status
ORDER BY coverage_status DESC, req.name"""

MILESTONE_READINESS_CYPHER = """\
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
ORDER BY ts.name"""

# --- Expected schema ---

EXPECTED_CONSTRAINTS = [
    ("Product", "product_id"),
    ("TechnologyDomain", "technology_domain_id"),
    ("Component", "component_id"),
    ("Requirement", "requirement_id"),
    ("TestSet", "test_set_id"),
    ("TestCase", "test_case_id"),
    ("Defect", "defect_id"),
    ("Change", "change_proposal_id"),
    ("Milestone", "milestone_id"),
    ("MaturityLevel", "name"),
    ("Resource", "name"),
]

EXPECTED_INDEXES = [
    ("Requirement", "type"),
    ("TestCase", "status"),
    ("Defect", "severity"),
    ("Defect", "status"),
    ("Change", "status"),
]

EXPECTED_VECTOR_INDEXES = [
    ("requirementEmbeddings", "Requirement", "embedding", 1536),
    ("defectEmbeddings", "Defect", "embedding", 1536),
]

EXPECTED_NODE_COUNTS = {
    "Product": 1,
    "TechnologyDomain": 4,
    "Component": 12,
    "Requirement": 70,
    "TestSet": 42,
    "TestCase": 136,
    "Defect": 26,
    "Change": 10,
    "Milestone": 5,
    "MaturityLevel": 4,
    "Resource": 129,
}

EXPECTED_REL_TYPES = [
    "PRODUCT_HAS_DOMAIN",
    "DOMAIN_HAS_COMPONENT",
    "COMPONENT_HAS_REQ",
    "TESTED_WITH",
    "CONTAINS_TEST_CASE",
    "DETECTED",
    "CHANGE_AFFECTS_REQ",
    "REQUIRES_ML",
    "REQUIRES_FLAWLESS_TEST_SET",
    "REQUIRES",
    "NEXT",
]


@dataclass
class AgentTools:
    """Container for individually-callable tools and shared resources."""

    driver: Driver
    get_component_overview: callable
    get_test_coverage: callable
    get_milestone_readiness: callable
    search_requirement_content: callable
    query_database: callable
    vector_store: Neo4jVector
    cypher_chain: GraphCypherQAChain


def build_tools(settings: Settings) -> AgentTools:
    """Build all 5 tools and return them individually (no agent)."""

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )
    driver.verify_connectivity()

    api_key = settings.openai_api_key.get_secret_value()
    llm = ChatOpenAI(model="gpt-4o", api_key=api_key)

    # --- Tool 1: get_component_overview ---
    @tool
    def get_component_overview(component_name: str) -> str:
        """Get comprehensive overview of a component including its requirements, technology domain, and associated defects. Example component names: HVB_3900, PDU_1500"""
        records, _, _ = driver.execute_query(
            COMPONENT_OVERVIEW_CYPHER, component_name=component_name
        )
        if not records:
            return f"No component found with name '{component_name}'"
        return json.dumps([dict(r) for r in records], indent=2, default=str)

    # --- Tool 2: get_test_coverage ---
    @tool
    def get_test_coverage(component_name: str) -> str:
        """Get the test coverage for a component showing all requirements and their assigned test sets. Shows which requirements are covered by tests. Example component names: HVB_3900, PDU_1500"""
        records, _, _ = driver.execute_query(
            TEST_COVERAGE_CYPHER, component_name=component_name
        )
        if not records:
            return f"No requirements found for component '{component_name}'"
        return json.dumps([dict(r) for r in records], indent=2, default=str)

    # --- Tool 3: get_milestone_readiness ---
    @tool
    def get_milestone_readiness(milestone_id: str) -> str:
        """Get what needs to be done to achieve a milestone. Returns open test sets, open defects, and estimated effort. Example milestone IDs: m_200, m_300, m_400"""
        records, _, _ = driver.execute_query(
            MILESTONE_READINESS_CYPHER, milestone_id=milestone_id
        )
        if not records:
            return f"No milestone found with ID '{milestone_id}'"
        return json.dumps([dict(r) for r in records], indent=2, default=str)

    # --- Tool 4: search_requirement_content ---
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=api_key)

    vector_store = Neo4jVector.from_existing_index(
        embedding=embeddings,
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password.get_secret_value(),
        index_name="requirementEmbeddings",
        node_label="Requirement",
        embedding_node_property="embedding",
        text_node_property="description",
    )

    @tool
    def search_requirement_content(query: str) -> str:
        """Search manufacturing requirement descriptions semantically to find relevant passages about specific topics, specifications, or engineering standards."""
        docs = vector_store.similarity_search(query, k=5)
        if not docs:
            return "No matching requirements found."
        results = [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
        return json.dumps(results, indent=2, default=str)

    # --- Tool 5: query_database (Text2Cypher) ---
    graph = Neo4jGraph(
        url=settings.neo4j_uri,
        username=settings.neo4j_username,
        password=settings.neo4j_password.get_secret_value(),
    )
    graph.refresh_schema()

    cypher_chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=False,
        allow_dangerous_requests=True,
    )

    @tool
    def query_database(question: str) -> str:
        """Query the manufacturing knowledge graph using natural language. Translates questions into Cypher queries for flexible data exploration about products, components, requirements, test cases, defects, and changes."""
        result = cypher_chain.invoke({"query": question})
        return result.get("result", str(result))

    return AgentTools(
        driver=driver,
        get_component_overview=get_component_overview,
        get_test_coverage=get_test_coverage,
        get_milestone_readiness=get_milestone_readiness,
        search_requirement_content=search_requirement_content,
        query_database=query_database,
        vector_store=vector_store,
        cypher_chain=cypher_chain,
    )


def build_agent(settings: Settings):
    """Construct the LangGraph ReAct agent with all 5 tools."""
    tools = build_tools(settings)

    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.openai_api_key.get_secret_value(),
    )

    agent = create_react_agent(
        model=llm,
        tools=[
            tools.get_component_overview,
            tools.get_test_coverage,
            tools.get_milestone_readiness,
            tools.search_requirement_content,
            tools.query_database,
        ],
        prompt=SYSTEM_PROMPT,
    )
    return agent, tools.driver
