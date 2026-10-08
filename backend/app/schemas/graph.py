from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    COMPANY = "Company"
    PERSON = "Person"
    STARTUP = "Startup"
    PRODUCT = "Product"
    TECHNOLOGY = "Technology"
    INVESTOR = "Investor"
    INDUSTRY = "Industry"
    ACQUISITION = "Acquisition"
    FUNDING_ROUND = "FundingRound"
    LOCATION = "Location"
    DOCUMENT = "Document"


class RelationshipType(str, Enum):
    FOUNDED = "FOUNDED"
    FOUNDED_BY = "FOUNDED_BY"
    CEO_OF = "CEO_OF"
    WORKED_AT = "WORKED_AT"
    ACQUIRED = "ACQUIRED"
    INVESTED_IN = "INVESTED_IN"
    COMPETES_WITH = "COMPETES_WITH"
    PARTNERED_WITH = "PARTNERED_WITH"
    DEVELOPED = "DEVELOPED"
    OPERATES_IN = "OPERATES_IN"
    RAISED = "RAISED"
    ANNOUNCED = "ANNOUNCED"
    MENTIONED_IN = "MENTIONED_IN"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    BOARD_MEMBER_OF = "BOARD_MEMBER_OF"


class EntityBase(BaseModel):
    name: str = Field(..., description="Canonical entity name")
    type: str = Field(..., description="Entity node type (e.g. Company, Person)")
    aliases: List[str] = Field(default_factory=list, description="Known aliases for entity resolution")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence")
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    source_document_id: Optional[str] = None
    source_chunk_id: Optional[str] = None
    source_page: Optional[int] = None


class EntityResponse(EntityBase):
    id: str
    user_id: str
    created_at: Optional[datetime] = None
    source_document_ids: List[str] = Field(default_factory=list)


class RelationshipBase(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_document_id: str = Field(..., description="Evidence document ID")
    source_chunk_id: Optional[str] = None
    source_page: Optional[int] = None
    valid_from: Optional[int] = Field(None, description="Starting year or timestamp")
    valid_to: Optional[int] = Field(None, description="Ending year or timestamp")
    properties: Dict[str, Any] = Field(default_factory=dict)


class RelationshipCreate(RelationshipBase):
    pass


class RelationshipResponse(RelationshipBase):
    id: str
    user_id: str
    source_entity_name: Optional[str] = None
    source_entity_type: Optional[str] = None
    target_entity_name: Optional[str] = None
    target_entity_type: Optional[str] = None
    created_at: Optional[datetime] = None


# Visualization and Neighbor Structures (React Flow / Cytoscape compatible)
class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    confidence: float = 1.0
    source_document: Optional[str] = None
    valid_from: Optional[int] = None
    valid_to: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphVisualizationResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class EntityDetailResponse(BaseModel):
    entity: EntityResponse
    relationships: List[RelationshipResponse]
    neighbors: List[GraphNode]


class GraphSearchRequest(BaseModel):
    query: str
    entity_types: Optional[List[str]] = None
    limit: int = Field(default=20, ge=1, le=100)
