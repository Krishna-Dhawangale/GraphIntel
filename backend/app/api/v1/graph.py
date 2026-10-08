from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request

from app.core.exceptions import NotFoundException
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.audit import AuditAction
from app.models.user import User
from app.schemas.graph import (
    EntityDetailResponse,
    EntityResponse,
    GraphVisualizationResponse,
    RelationshipResponse,
)
from app.security.deps import require_analyst, require_user
from app.services.audit_service import log_audit_event
from app.services.graph_service import GraphService

router = APIRouter()


def get_graph_service() -> GraphService:
    return GraphService()


@router.get(
    "/entities/{id}",
    response_model=EntityResponse,
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_entities"))],
)
async def get_entity_by_id(
    id: str,
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Retrieve an entity by its unique ID for the current user."""
    entity = await service.store.get_entity(user_id=current_user.id, entity_id=id)
    if not entity:
        raise NotFoundException(f"Entity with ID '{id}' was not found.")
    return entity


@router.get(
    "/entities/{id}/relationships",
    response_model=List[RelationshipResponse],
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_rels"))],
)
async def get_entity_relationships(
    id: str,
    direction: str = Query("both", pattern="^(both|inbound|outbound)$"),
    rel_type: Optional[str] = Query(None, description="Comma-separated relationship types"),
    year: Optional[int] = Query(None, description="Filter for temporal year"),
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Retrieve relationships connected to an entity with optional temporal filtering."""
    rel_types_list = [r.strip().upper() for r in rel_type.split(",")] if rel_type else None
    return await service.get_entity_relationships(
        user_id=current_user.id,
        entity_id=id,
        direction=direction,
        relationship_types=rel_types_list,
        temporal_year=year,
    )


@router.get(
    "/graph/entity/{id}",
    response_model=EntityDetailResponse,
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_detail"))],
)
async def get_entity_graph_detail(
    id: str,
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Retrieve complete graph detail for an entity (entity, relationships, and neighbor nodes)."""
    detail = await service.get_entity_detail(user_id=current_user.id, entity_id=id)
    if not detail:
        raise NotFoundException(f"Entity with ID '{id}' was not found.")
    return detail


@router.get(
    "/graph/neighbors/{id}",
    response_model=GraphVisualizationResponse,
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_neighbors"))],
)
async def get_graph_neighbors(
    id: str,
    max_hops: int = Query(1, ge=1, le=5),
    rel_type: Optional[str] = Query(None, description="Filter by relationship types"),
    year: Optional[int] = Query(None, description="Filter for temporal year"),
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Traverse graph neighborhood up to max_hops formatted for React Flow or Cytoscape visualization."""
    rel_types_list = [r.strip().upper() for r in rel_type.split(",")] if rel_type else None
    return await service.get_neighbors(
        user_id=current_user.id,
        entity_id=id,
        max_hops=max_hops,
        relationship_types=rel_types_list,
        temporal_year=year,
    )


@router.get(
    "/graph/search",
    response_model=List[EntityResponse],
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_search"))],
)
async def search_graph_entities(
    q: str = Query("", description="Entity search query (name or alias)"),
    entity_type: Optional[str] = Query(None, description="Entity type filter"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Search for entities matching query text and type within user's graph."""
    types_list = [entity_type] if entity_type else None
    return await service.store.search_entities(
        user_id=current_user.id,
        query=q,
        entity_types=types_list,
        limit=limit,
    )


@router.get(
    "/graph/visualization",
    response_model=GraphVisualizationResponse,
    tags=["Knowledge Graph"],
    dependencies=[Depends(rate_limit(max_requests=60, window_seconds=60, key_prefix="graph_vis"))],
)
async def get_graph_visualization(
    limit: int = Query(150, ge=1, le=500),
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
):
    """Retrieve full graph visualization for user."""
    return await service.store.get_full_graph(user_id=current_user.id, limit=limit)


@router.get(
    "/graph/paths",
    response_model=List[Dict[str, Any]],
    tags=["Knowledge Graph"],
    dependencies=[Depends(require_user), Depends(rate_limit(max_requests=30, window_seconds=60, key_prefix="graph_paths"))],
)
async def find_paths_between_entities(
    request: Request,
    from_name: str = Query(..., description="Source entity name"),
    to_name: Optional[str] = Query(None, description="Target entity name"),
    max_depth: int = Query(3, ge=1, le=5),
    current_user: User = Depends(require_user),
    service: GraphService = Depends(get_graph_service),
    db=Depends(get_db),
):
    """Multi-hop path exploration between two entities."""
    # Find start entity ID
    start_ent = await service.store.get_entity_by_name(user_id=current_user.id, name=from_name)
    end_ent = await service.store.get_entity_by_name(user_id=current_user.id, name=to_name) if to_name else None

    if not start_ent:
        return []

    paths = await service.store.find_paths(
        user_id=current_user.id,
        start_entity_id=start_ent.id,
        end_entity_id=end_ent.id if end_ent else None,
        max_hops=max_depth,
    )

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    await log_audit_event(
        db=db,
        action=AuditAction.GRAPH_QUERY.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        resource_type="graph_path",
        status="SUCCESS",
        ip_address=client_ip,
        user_agent=user_agent,
        metadata={"from": from_name, "to": to_name, "depth": max_depth, "paths_found": len(paths)},
    )

    return paths
