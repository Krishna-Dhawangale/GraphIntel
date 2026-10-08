import asyncio
import time
from typing import Dict, List, Optional, Tuple

from app.schemas.query import EvidenceItem, GraphPathInfo, RetrievedChunk
from app.services.graph_retriever import GraphRetriever
from app.services.reranker import get_reranker
from app.services.retrieval_planner import RetrievalPlan, RetrievalPlanner
from app.services.retrieval_service import RetrievalService


class HybridRetriever:
    """Orchestrates parallel vector search and graph retrieval with evidence fusion and reranking."""

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        graph_retriever: Optional[GraphRetriever] = None,
    ):
        self.vector_retriever = retrieval_service or RetrievalService()
        self.graph_retriever = graph_retriever or GraphRetriever()
        self.planner = RetrievalPlanner()
        self.reranker = get_reranker()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        retrieval_mode: Optional[str] = "hybrid",
        top_k: int = 5,
        max_graph_hops: int = 3,
        document_ids: Optional[List[str]] = None,
        temporal_year: Optional[int] = None,
    ) -> Tuple[List[EvidenceItem], List[RetrievedChunk], List[GraphPathInfo], List[str], Dict[str, int]]:
        """
        Executes hybrid retrieval according to plan.
        Returns:
            (fused_evidence, retrieved_chunks, graph_paths, entities, timing_metrics)
        """
        plan: RetrievalPlan = self.planner.plan(
            question=query,
            user_override_mode=retrieval_mode,
            max_graph_hops=max_graph_hops,
            temporal_year=temporal_year,
        )

        all_evidence: List[EvidenceItem] = []
        retrieved_chunks: List[RetrievedChunk] = []
        graph_paths: List[GraphPathInfo] = []
        matched_entities: List[str] = []

        vector_time_ms = 0
        graph_time_ms = 0
        rerank_time_ms = 0

        # Run vector retrieval if requested by plan
        vector_task = None
        if plan.use_vector:
            t0 = time.time()
            vector_task = self.vector_retriever.retrieve(
                query=query,
                user_id=user_id,
                top_k=top_k,
                filters=document_ids,
            )

        # Run graph retrieval if requested by plan
        graph_task = None
        if plan.use_graph:
            entities_to_query = plan.target_entities or [query]
            graph_task = self.graph_retriever.retrieve(
                user_id=user_id,
                entities=entities_to_query,
                relationships=plan.target_relationships,
                max_hops=plan.max_hops,
                temporal_year=plan.temporal_year,
                limit=top_k * 2,
            )

        degraded = False
        fallback_reason = None

        # Execute retrieval with graceful degradation
        if vector_task and graph_task:
            results = await asyncio.gather(vector_task, graph_task, return_exceptions=True)
            v_res_raw, g_res_raw = results[0], results[1]

            if isinstance(v_res_raw, Exception) and isinstance(g_res_raw, Exception):
                raise v_res_raw

            if isinstance(v_res_raw, Exception):
                degraded = True
                fallback_reason = f"Vector retrieval error: {str(v_res_raw)}"
                try:
                    from app.core.metrics import record_degraded_event
                    record_degraded_event("vector_retrieval_failure")
                except Exception:
                    pass
                retrieved_chunks = []
            else:
                retrieved_chunks = v_res_raw

            if isinstance(g_res_raw, Exception):
                degraded = True
                fallback_reason = f"Graph retrieval error: {str(g_res_raw)}"
                try:
                    from app.core.metrics import record_degraded_event
                    record_degraded_event("graph_retrieval_failure")
                except Exception:
                    pass
                graph_evidence, graph_paths, matched_entities = [], [], []
            else:
                graph_evidence, graph_paths, matched_entities = g_res_raw
                all_evidence.extend(graph_evidence)

        elif vector_task:
            t0 = time.time()
            try:
                retrieved_chunks = await vector_task
            except Exception as e:
                degraded = True
                fallback_reason = f"Vector retrieval error: {str(e)}"
                retrieved_chunks = []
            vector_time_ms = int((time.time() - t0) * 1000)

        elif graph_task:
            t0 = time.time()
            try:
                graph_evidence, graph_paths, matched_entities = await graph_task
                all_evidence.extend(graph_evidence)
            except Exception as e:
                degraded = True
                fallback_reason = f"Graph retrieval error: {str(e)}"
                graph_evidence, graph_paths, matched_entities = [], [], []
            graph_time_ms = int((time.time() - t0) * 1000)

        # Convert vector chunks to normalized EvidenceItems
        for chunk in retrieved_chunks:
            all_evidence.append(
                EvidenceItem(
                    type="vector",
                    content=f"Document excerpt ({chunk.filename}, page {chunk.page_number or 'N/A'}): {chunk.text}",
                    source_document=chunk.document_id,
                    page=chunk.page_number,
                    confidence=chunk.score,
                )
            )

        # Rerank fused evidence
        t_rr_start = time.time()
        fused_evidence = self.reranker.rerank(
            query=query,
            evidence_items=all_evidence,
            top_k=top_k * 2,
        )
        rerank_time_ms = int((time.time() - t_rr_start) * 1000)

        timing_metrics = {
            "vector_time_ms": vector_time_ms,
            "graph_time_ms": graph_time_ms,
            "rerank_time_ms": rerank_time_ms,
            "paths_found": len(graph_paths),
            "graph_nodes_retrieved": len(matched_entities),
            "degraded": degraded,
            "fallback_reason": fallback_reason,
        }

        return fused_evidence, retrieved_chunks, graph_paths, matched_entities, timing_metrics
