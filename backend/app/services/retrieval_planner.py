from dataclasses import dataclass, field
from typing import List, Optional
from app.core.config import settings
from app.services.query_analyzer import QueryAnalysis, QueryAnalyzer


@dataclass
class RetrievalPlan:
    mode: str  # "vector", "graph", "hybrid"
    use_vector: bool
    use_graph: bool
    max_hops: int
    temporal_year: Optional[int] = None
    target_entities: List[str] = field(default_factory=list)
    target_relationships: List[str] = field(default_factory=list)


class RetrievalPlanner:
    """Creates deterministic and safe retrieval plans for GraphRAG queries."""

    def __init__(self):
        self.analyzer = QueryAnalyzer()

    def plan(
        self,
        question: str,
        user_override_mode: Optional[str] = None,
        max_graph_hops: Optional[int] = None,
        temporal_year: Optional[int] = None,
    ) -> RetrievalPlan:
        analysis: QueryAnalysis = self.analyzer.analyze(question)

        # Determine effective mode
        if user_override_mode and user_override_mode.lower() in ("vector", "graph", "hybrid"):
            effective_mode = user_override_mode.lower()
        else:
            effective_mode = analysis.suggested_mode

        use_vector = effective_mode in ("vector", "hybrid")
        use_graph = effective_mode in ("graph", "hybrid")

        # Determine hops
        if max_graph_hops:
            hops = min(max_graph_hops, settings.MAX_GRAPH_HOPS)
        else:
            hops = min(analysis.suggested_hops, settings.MAX_GRAPH_HOPS)

        # Determine temporal anchor
        year = temporal_year
        if year is None and analysis.temporal_years:
            year = analysis.temporal_years[0]

        return RetrievalPlan(
            mode=effective_mode,
            use_vector=use_vector,
            use_graph=use_graph,
            max_hops=hops,
            temporal_year=year,
            target_entities=analysis.entities,
            target_relationships=analysis.relationships,
        )
