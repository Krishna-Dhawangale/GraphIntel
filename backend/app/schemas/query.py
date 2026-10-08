from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"


class QueryRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, max_length=2000, description="User search query or question"
    )
    retrieval_mode: Optional[str] = Field(
        default="hybrid", description="Retrieval mode: vector, graph, or hybrid"
    )
    top_k: Optional[int] = Field(
        default=5, ge=1, le=50, description="Number of vector chunks to retrieve"
    )
    max_graph_hops: Optional[int] = Field(
        default=3, ge=1, le=5, description="Maximum graph traversal hops"
    )
    document_ids: Optional[List[str]] = Field(
        default=None, description="Optional filter for specific document IDs"
    )
    temporal_year: Optional[int] = Field(
        default=None, description="Optional filter for specific temporal year"
    )


class SourceCitation(BaseModel):
    document_id: str
    filename: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None
    citation_order: int
    relevance_score: float


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    score: float


class GraphPathInfo(BaseModel):
    length: int
    nodes: List[str]
    node_types: List[str]
    relationships: List[str]
    evidence_docs: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    type: str = Field(..., description="Evidence type: 'vector', 'graph', or 'metadata'")
    content: str
    entity: Optional[str] = None
    relationship: Optional[str] = None
    target: Optional[str] = None
    source_document: Optional[str] = None
    page: Optional[int] = None
    confidence: float = 1.0
    valid_from: Optional[int] = None
    valid_to: Optional[int] = None


class QueryMetadata(BaseModel):
    retrieval_time_ms: int
    llm_time_ms: int
    total_time_ms: int
    chunks_retrieved: int
    model_used: str
    graph_retrieval_time_ms: int = 0
    vector_retrieval_time_ms: int = 0
    rerank_time_ms: int = 0
    paths_found: int = 0
    graph_nodes_retrieved: int = 0
    degraded: bool = False
    fallback_reason: Optional[str] = None
    tokens_used: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class QueryResponse(BaseModel):
    id: Optional[str] = None
    question: str
    answer: str
    sources: List[SourceCitation]
    retrieved_chunks: List[RetrievedChunk]
    graph_paths: List[GraphPathInfo] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    retrieval_mode: str = "hybrid"
    evidence: List[EvidenceItem] = Field(default_factory=list)
    metadata: QueryMetadata


class QueryHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    answer: str
    retrieval_time_ms: int
    llm_time_ms: int
    created_at: datetime
    sources_count: int
