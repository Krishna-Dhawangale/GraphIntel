from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    answer_generator_node,
    citation_validator_node,
    entity_resolver_node,
    evidence_evaluator_node,
    fact_checker_node,
    query_analyzer_node,
    research_agent_node,
    retrieval_planner_node,
    retriever_node,
)
from app.agent.state import AgentState


def route_after_evaluation(state: AgentState) -> str:
    """Conditional router determining whether to research more or generate answer."""
    if state.get("should_research_more", False) and state.get("iteration_count", 0) < 2:
        return "research_agent"
    return "answer_generator"


def create_agent_graph() -> StateGraph:
    """Constructs the complete Agentic GraphRAG LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("query_analyzer", query_analyzer_node)
    workflow.add_node("entity_resolver", entity_resolver_node)
    workflow.add_node("retrieval_planner", retrieval_planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("evidence_evaluator", evidence_evaluator_node)
    workflow.add_node("research_agent", research_agent_node)
    workflow.add_node("answer_generator", answer_generator_node)
    workflow.add_node("fact_checker", fact_checker_node)
    workflow.add_node("citation_validator", citation_validator_node)

    # 2. Sequential Edges
    workflow.add_edge(START, "query_analyzer")
    workflow.add_edge("query_analyzer", "entity_resolver")
    workflow.add_edge("entity_resolver", "retrieval_planner")
    workflow.add_edge("retrieval_planner", "retriever")
    workflow.add_edge("retriever", "evidence_evaluator")

    # 3. Conditional Branch from Evidence Evaluator
    workflow.add_conditional_edges(
        "evidence_evaluator",
        route_after_evaluation,
        {
            "research_agent": "research_agent",
            "answer_generator": "answer_generator",
        },
    )

    # Loop research agent back to evaluator
    workflow.add_edge("research_agent", "evidence_evaluator")

    # Finalization Pipeline
    workflow.add_edge("answer_generator", "fact_checker")
    workflow.add_edge("fact_checker", "citation_validator")
    workflow.add_edge("citation_validator", END)

    return workflow


# Compile singleton workflow instance
agent_workflow = create_agent_graph().compile()
