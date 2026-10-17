import asyncio
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.query import EvidenceItem, GraphPathInfo, RetrievedChunk
from app.services.graph_retriever import GraphRetriever
from app.services.reranker import get_reranker
from app.services.retrieval_planner import RetrievalPlan, RetrievalPlanner
from app.services.retrieval_service import RetrievalService


class HybridRetriever:
    """Orchestrates parallel vector search and graph retrieval with evidence fusion, deduplication, and reranking."""

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
    ) -> Tuple[List[EvidenceItem], List[RetrievedChunk], List[GraphPathInfo], List[str], Dict[str, Any]]:
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
        degraded = False
        fallback_reason = None

        # Effective top_k: increase for financial queries to ensure table context is retrieved
        effective_top_k = max(top_k, 7) if plan.is_financial else top_k

        async def _run_vector() -> Tuple[List[RetrievedChunk], int]:
            t_start = time.perf_counter()
            chunks = await self.vector_retriever.retrieve(
                query=query,
                user_id=user_id,
                top_k=effective_top_k,
                filters=document_ids,
            )
            elapsed = int((time.perf_counter() - t_start) * 1000)
            return chunks, elapsed

        async def _run_graph() -> Tuple[Tuple[List[EvidenceItem], List[GraphPathInfo], List[str]], int]:
            t_start = time.perf_counter()
            entities_to_query = plan.target_entities or [query]
            res = await self.graph_retriever.retrieve(
                user_id=user_id,
                entities=entities_to_query,
                relationships=plan.target_relationships,
                max_hops=plan.max_hops,
                temporal_year=plan.temporal_year,
                limit=top_k * 2,
            )
            elapsed = int((time.perf_counter() - t_start) * 1000)
            return res, elapsed

        # 1. Parallel or selective retrieval
        if plan.use_vector and plan.use_graph:
            results = await asyncio.gather(_run_vector(), _run_graph(), return_exceptions=True)
            v_res, g_res = results[0], results[1]

            if isinstance(v_res, Exception) and isinstance(g_res, Exception):
                raise v_res

            if isinstance(v_res, Exception):
                degraded = True
                fallback_reason = f"Vector retrieval error: {str(v_res)}"
                retrieved_chunks = []
                vector_time_ms = 0
            else:
                retrieved_chunks, vector_time_ms = v_res

            if isinstance(g_res, Exception):
                degraded = True
                fallback_reason = f"Graph retrieval error: {str(g_res)}"
                graph_evidence, graph_paths, matched_entities = [], [], []
                graph_time_ms = 0
            else:
                (graph_evidence, graph_paths, matched_entities), graph_time_ms = g_res
                all_evidence.extend(graph_evidence)

        elif plan.use_vector:
            try:
                retrieved_chunks, vector_time_ms = await _run_vector()
            except Exception as e:
                degraded = True
                fallback_reason = f"Vector retrieval error: {str(e)}"
                retrieved_chunks = []
                vector_time_ms = 0

        elif plan.use_graph:
            try:
                (graph_evidence, graph_paths, matched_entities), graph_time_ms = await _run_graph()
                all_evidence.extend(graph_evidence)
            except Exception as e:
                degraded = True
                fallback_reason = f"Graph retrieval error: {str(e)}"
                graph_evidence, graph_paths, matched_entities = [], [], []
                graph_time_ms = 0

        # 2. Deduplicate retrieved chunks and convert to EvidenceItems
        seen_chunk_ids: Set[str] = set()
        unique_chunks: List[RetrievedChunk] = []
        for chunk in retrieved_chunks:
            if chunk.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk.chunk_id)
            unique_chunks.append(chunk)

            page_label = f"Page {chunk.page_number}" if chunk.page_number is not None else "Page N/A"
            section_label = f" [{chunk.section}]" if chunk.section else ""
            all_evidence.append(
                EvidenceItem(
                    type="vector",
                    content=f"Document excerpt ({chunk.filename}, {page_label}{section_label}): {chunk.text}",
                    source_document=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    page=chunk.page_number,
                    confidence=chunk.score,
                )
            )

        retrieved_chunks = unique_chunks

        # 3. Deduplicate graph paths: exclude paths with length < 2 or duplicate node cycles
        cleaned_paths: List[GraphPathInfo] = []
        seen_path_keys: Set[str] = set()

        for p in graph_paths:
            # Multi-hop paths must have at least 2 distinct edges
            if p.length < 2:
                continue
            # Must not contain duplicate cycle nodes
            if len(p.nodes) != len(set(p.nodes)):
                continue
            path_key = "-".join(p.nodes) + ":" + "-".join(p.relationships)
            if path_key in seen_path_keys:
                continue
            seen_path_keys.add(path_key)
            cleaned_paths.append(p)

        graph_paths = cleaned_paths

        # 4. Deduplicate EvidenceItems
        dedup_evidence: List[EvidenceItem] = []
        seen_evidence_signatures: Set[str] = set()

        for item in all_evidence:
            sig = f"{item.type}:{item.source_document}:{item.page}:{item.content[:100]}"
            if sig not in seen_evidence_signatures:
                seen_evidence_signatures.add(sig)
                dedup_evidence.append(item)

        # 5. Rerank fused evidence
        t_rr_start = time.perf_counter()
        fused_evidence = self.reranker.rerank(
            query=query,
            evidence_items=dedup_evidence,
            top_k=max(top_k * 2, 10),
        )
        rerank_time_ms = int((time.perf_counter() - t_rr_start) * 1000)

        timing_metrics = {
            "vector_time_ms": vector_time_ms,
            "graph_time_ms": graph_time_ms,
            "rerank_time_ms": rerank_time_ms,
            "paths_found": len(graph_paths),
            "graph_nodes_retrieved": len(matched_entities),
            "degraded": degraded,
            "fallback_reason": fallback_reason,
            "category": plan.category,
        }

        return fused_evidence, retrieved_chunks, graph_paths, matched_entities, timing_metrics
