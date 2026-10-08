import time
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.workflow import agent_workflow
from app.core.logging import log_event, logger
from app.models.query import Query, Source
from app.schemas.query import QueryMetadata, QueryResponse


class AgentRAGService:
    """Agentic RAG orchestrator using LangGraph workflow with full safety and persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        question: str,
        user_id: str,
        conversation_id: Optional[str] = None,
    ) -> QueryResponse:
        start_total = time.time()
        clean_q = question.strip()

        initial_state: AgentState = {
            "user_id": user_id,
            "question": clean_q,
            "conversation_id": conversation_id,
            "iteration_count": 0,
            "errors": [],
            "execution_trace": [],
            "research_steps": [],
        }

        log_event(
            "agent_workflow_started",
            f"Starting LangGraph Agentic RAG for: '{clean_q}'",
            user_id=user_id,
        )

        try:
            final_state: AgentState = await agent_workflow.ainvoke(initial_state)
        except Exception as e:
            logger.exception(f"LangGraph execution exception: {e}")
            final_state = {
                "answer": (
                    "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question. "
                    "An error occurred while executing the reasoning agent."
                ),
                "citations": [],
                "vector_results": [],
                "graph_paths": [],
                "evidence": [],
                "resolved_entities": [],
                "execution_trace": [{"error": str(e)}],
            }

        total_time_ms = int((time.time() - start_total) * 1000)

        # Compute timings from execution trace
        trace = final_state.get("execution_trace", [])
        retrieval_ms = sum(
            t.get("latency_ms", 0) for t in trace if t.get("node") in ("retriever", "research_agent")
        )
        llm_ms = sum(
            t.get("latency_ms", 0) for t in trace if t.get("node") == "answer_generator"
        )

        citations = final_state.get("citations", [])
        retrieved_chunks = final_state.get("vector_results", [])
        graph_paths = final_state.get("graph_paths", [])
        evidence_items = final_state.get("evidence", [])
        resolved_entities = [
            r["canonical"] for r in final_state.get("resolved_entities", []) if "canonical" in r
        ]

        # Persist to database
        query_record = Query(
            user_id=user_id,
            question=clean_q,
            answer=final_state.get("answer", ""),
            retrieval_time_ms=retrieval_ms,
            llm_time_ms=llm_ms,
        )
        self.db.add(query_record)
        await self.db.flush()

        for cit in citations:
            source_record = Source(
                query_id=query_record.id,
                document_id=cit.document_id,
                chunk_id=cit.chunk_id,
                relevance_score=cit.relevance_score,
                citation_order=cit.citation_order,
            )
            self.db.add(source_record)

        await self.db.commit()

        from app.core.cost_tracker import cost_tracker
        from app.core.metrics import record_token_usage

        # Estimate agent token usage based on research steps and answer
        approx_prompt_tokens = max(100, len(clean_q) * 2 + len(evidence_items) * 40)
        approx_completion_tokens = max(50, len(final_state.get("answer", "")) // 4)
        total_tokens = approx_prompt_tokens + approx_completion_tokens
        agent_cost = cost_tracker.calculate_cost("gpt-4o", approx_prompt_tokens, approx_completion_tokens)
        try:
            record_token_usage("langgraph-agentic-v1", approx_prompt_tokens, approx_completion_tokens)
        except Exception:
            pass

        metadata = QueryMetadata(
            retrieval_time_ms=retrieval_ms,
            llm_time_ms=llm_ms,
            total_time_ms=total_time_ms,
            chunks_retrieved=len(retrieved_chunks),
            model_used="langgraph-agentic-v1",
            graph_retrieval_time_ms=retrieval_ms,
            vector_retrieval_time_ms=retrieval_ms,
            paths_found=len(graph_paths),
            graph_nodes_retrieved=len(resolved_entities),
            tokens_used=total_tokens,
            estimated_cost_usd=agent_cost,
        )

        return QueryResponse(
            id=query_record.id,
            question=clean_q,
            answer=final_state.get("answer", ""),
            sources=citations,
            retrieved_chunks=retrieved_chunks,
            graph_paths=graph_paths,
            entities=resolved_entities,
            retrieval_mode="agentic",
            evidence=evidence_items,
            metadata=metadata,
        )
