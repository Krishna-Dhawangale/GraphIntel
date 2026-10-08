from typing import Any, Dict, List, Optional, TypedDict
from app.schemas.query import EvidenceItem, GraphPathInfo, RetrievedChunk, SourceCitation


class AgentState(TypedDict, total=False):
    """LangGraph shared state for Agentic GraphRAG."""
    user_id: str
    question: str
    conversation_id: Optional[str]
    entities: List[str]
    resolved_entities: List[Dict[str, Any]]
    intent: str
    filters: Dict[str, Any]
    retrieval_plan: Dict[str, Any]
    vector_results: List[RetrievedChunk]
    graph_results: List[EvidenceItem]
    evidence: List[EvidenceItem]
    graph_paths: List[GraphPathInfo]
    answer: str
    citations: List[SourceCitation]
    confidence: float
    errors: List[str]
    iteration_count: int
    should_research_more: bool
    research_steps: List[str]
    execution_trace: List[Dict[str, Any]]
