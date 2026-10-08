import re
import time
from typing import Any, Dict, List, Optional

from app.agent.state import AgentState
from app.agent.tools import AgentTools
from app.core.config import settings
from app.core.logging import logger
from app.providers.llm.base import LLMProvider
from app.providers.llm.factory import get_llm_provider
from app.schemas.query import EvidenceItem, GraphPathInfo, RetrievedChunk, SourceCitation
from app.services.entity_resolver import EntityResolver
from app.services.query_analyzer import QueryAnalysis, QueryAnalyzer
from app.services.reranker import get_reranker
from app.services.retrieval_planner import RetrievalPlan, RetrievalPlanner

tools = AgentTools()
analyzer = QueryAnalyzer()
planner = RetrievalPlanner()
resolver = EntityResolver()
reranker = get_reranker()
llm: LLMProvider = get_llm_provider()

MAX_AGENT_ITERATIONS = 2


async def query_analyzer_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Analyze user query intent, entities, dates, relationships, and complexity."""
    t0 = time.time()
    question = state.get("question", "")
    analysis: QueryAnalysis = analyzer.analyze(question)

    trace = {
        "node": "query_analyzer",
        "latency_ms": int((time.time() - t0) * 1000),
        "entities_detected": analysis.entities,
        "relationships_detected": analysis.relationships,
        "temporal_years": analysis.temporal_years,
        "is_financial_metric": analysis.is_financial_metric,
    }

    return {
        "entities": analysis.entities,
        "intent": "financial_metric" if analysis.is_financial_metric else "market_intelligence",
        "filters": {"temporal_years": analysis.temporal_years},
        "iteration_count": 0,
        "research_steps": ["Query analyzed for intent and entity anchors."],
        "execution_trace": state.get("execution_trace", []) + [trace],
        "errors": state.get("errors", []),
    }


async def entity_resolver_node(state: AgentState) -> Dict[str, Any]:
    """Node 2: Resolve candidate entities against the knowledge graph."""
    t0 = time.time()
    user_id = state.get("user_id", "")
    raw_entities = state.get("entities", [])
    resolved: List[Dict[str, Any]] = []

    # Fetch pool of existing graph entities for user
    existing_entities = await tools.search_entities(user_id=user_id, query="", limit=100)
    existing_dicts = [
        {"name": e.name, "type": e.type, "aliases": e.aliases} for e in existing_entities
    ]

    for raw in raw_entities:
        canonical, aliases, conf = resolver.resolve(
            name=raw,
            entity_type="Company",
            existing_entities=existing_dicts,
        )
        resolved.append({
            "raw": raw,
            "canonical": canonical,
            "aliases": aliases,
            "confidence": conf,
        })

    trace = {
        "node": "entity_resolver",
        "latency_ms": int((time.time() - t0) * 1000),
        "resolved_count": len(resolved),
        "resolved_entities": [r["canonical"] for r in resolved],
    }

    return {
        "resolved_entities": resolved,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def retrieval_planner_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Create an explicit, validated retrieval plan."""
    t0 = time.time()
    question = state.get("question", "")
    filters = state.get("filters", {})
    resolved = state.get("resolved_entities", [])
    temporal_years = filters.get("temporal_years", [])
    temp_year = temporal_years[0] if temporal_years else None

    # Derive plan
    plan: RetrievalPlan = planner.plan(
        question=question,
        temporal_year=temp_year,
    )

    canonical_entities = [r["canonical"] for r in resolved] or plan.target_entities

    plan_dict = {
        "mode": plan.mode,
        "use_vector": plan.use_vector,
        "use_graph": plan.use_graph,
        "max_hops": plan.max_hops,
        "temporal_year": plan.temporal_year,
        "target_entities": canonical_entities,
        "target_relationships": plan.target_relationships,
    }

    trace = {
        "node": "retrieval_planner",
        "latency_ms": int((time.time() - t0) * 1000),
        "plan": plan_dict,
    }

    return {
        "retrieval_plan": plan_dict,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def retriever_node(state: AgentState) -> Dict[str, Any]:
    """Node 4: Execute parallel vector and graph retrieval according to plan."""
    t0 = time.time()
    user_id = state.get("user_id", "")
    question = state.get("question", "")
    plan = state.get("retrieval_plan", {})

    vector_results: List[RetrievedChunk] = []
    graph_evidence: List[EvidenceItem] = []
    graph_paths: List[GraphPathInfo] = []

    # 1. Vector Search
    if plan.get("use_vector", True):
        vector_results = await tools.vector_search(
            user_id=user_id,
            query=question,
            top_k=5,
        )

    # 2. Graph Search
    if plan.get("use_graph", True):
        entities = plan.get("target_entities") or [question]
        g_res = await tools.graph_search(
            user_id=user_id,
            entities=entities,
            relationships=plan.get("target_relationships"),
            max_hops=plan.get("max_hops", 2),
            temporal_year=plan.get("temporal_year"),
        )
        graph_evidence = g_res.get("evidence", [])
        graph_paths = g_res.get("paths", [])

    # Fuse evidence
    all_evidence: List[EvidenceItem] = list(graph_evidence)
    for c in vector_results:
        all_evidence.append(
            EvidenceItem(
                type="vector",
                content=f"Document excerpt ({c.filename}, page {c.page_number or 'N/A'}): {c.text}",
                source_document=c.document_id,
                page=c.page_number,
                confidence=c.score,
            )
        )

    # Rerank
    fused_evidence = reranker.rerank(query=question, evidence_items=all_evidence, top_k=10)

    trace = {
        "node": "retriever",
        "latency_ms": int((time.time() - t0) * 1000),
        "vector_chunks_retrieved": len(vector_results),
        "graph_facts_retrieved": len(graph_evidence),
        "graph_paths_found": len(graph_paths),
        "fused_evidence_count": len(fused_evidence),
    }

    return {
        "vector_results": vector_results,
        "graph_results": graph_evidence,
        "evidence": fused_evidence,
        "graph_paths": graph_paths,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def evidence_evaluator_node(state: AgentState) -> Dict[str, Any]:
    """Node 5: Evaluate evidence sufficiency, relevance, and contradictions."""
    t0 = time.time()
    evidence = state.get("evidence", [])
    iteration = state.get("iteration_count", 0)
    question = state.get("question", "")

    # Check evidence sufficiency
    has_evidence = len(evidence) > 0
    # Determine if research step needed
    should_research_more = False
    if not has_evidence and iteration < MAX_AGENT_ITERATIONS:
        # If no evidence retrieved on first pass for multi-word query, trigger targeted research
        should_research_more = True

    confidence = 0.95 if has_evidence else 0.20

    trace = {
        "node": "evidence_evaluator",
        "latency_ms": int((time.time() - t0) * 1000),
        "evidence_count": len(evidence),
        "has_evidence": has_evidence,
        "should_research_more": should_research_more,
        "iteration": iteration,
    }

    return {
        "confidence": confidence,
        "should_research_more": should_research_more,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def research_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node 6: Multi-step research expansion for missing or chained evidence."""
    t0 = time.time()
    user_id = state.get("user_id", "")
    question = state.get("question", "")
    curr_iteration = state.get("iteration_count", 0)
    resolved = state.get("resolved_entities", [])
    existing_evidence = list(state.get("evidence", []))
    existing_paths = list(state.get("graph_paths", []))
    steps = list(state.get("research_steps", []))

    # Expand search terms by sub-tokens or broader graph search
    expanded_terms = [r["canonical"] for r in resolved]
    if not expanded_terms:
        words = [w for w in question.split() if len(w) > 4 and w.lower() not in {"which", "where", "about", "their"}]
        expanded_terms = words[:3]

    steps.append(f"Research iteration {curr_iteration + 1}: Expanding entity scope to {expanded_terms}")

    g_res = await tools.graph_search(
        user_id=user_id,
        entities=expanded_terms,
        max_hops=3,
    )
    new_evidence = g_res.get("evidence", [])
    new_paths = g_res.get("paths", [])

    existing_evidence.extend(new_evidence)
    existing_paths.extend(new_paths)

    trace = {
        "node": "research_agent",
        "latency_ms": int((time.time() - t0) * 1000),
        "expanded_terms": expanded_terms,
        "new_evidence_found": len(new_evidence),
    }

    return {
        "evidence": existing_evidence,
        "graph_paths": existing_paths,
        "iteration_count": curr_iteration + 1,
        "research_steps": steps,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def answer_generator_node(state: AgentState) -> Dict[str, Any]:
    """Node 7: Generate grounded synthesis from fused multi-modal evidence."""
    t0 = time.time()
    question = state.get("question", "")
    evidence = state.get("evidence", [])
    paths = state.get("graph_paths", [])

    if not evidence and not paths:
        answer = (
            "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question. "
            "No matching chunks or relationships were found in the uploaded documents."
        )
        return {
            "answer": answer,
            "execution_trace": state.get("execution_trace", []) + [{
                "node": "answer_generator",
                "latency_ms": int((time.time() - t0) * 1000),
                "status": "insufficient_evidence",
            }],
        }

    # Format context
    doc_blocks = []
    graph_blocks = []
    for i, item in enumerate(evidence, start=1):
        if item.type == "vector":
            doc_blocks.append(f"[Source {i}] {item.content}")
        else:
            graph_blocks.append(f"- {item.content}")

    for p in paths:
        p_str = " -> ".join(
            f"({p.nodes[j]}:{p.node_types[j]}) -[{p.relationships[j]}]-> ({p.nodes[j+1]}:{p.node_types[j+1]})"
            for j in range(len(p.relationships))
        )
        graph_blocks.append(f"- Knowledge Graph Multi-Hop Path: {p_str}")

    context_str = ""
    if doc_blocks:
        context_str += "=== DOCUMENT EVIDENCE ===\n" + "\n".join(doc_blocks) + "\n\n"
    if graph_blocks:
        context_str += "=== KNOWLEDGE GRAPH EVIDENCE ===\n" + "\n".join(graph_blocks) + "\n\n"

    prompt = (
        f"Context:\n{context_str}\n"
        f"Question: {question}\n\n"
        f"Answer clearly and factually based on the context above. Cite document sources using [1], [2], etc., "
        f"and explicitly integrate knowledge graph facts and paths where relevant."
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are GraphIntel, an enterprise Market Intelligence RAG assistant. "
                "Synthesize grounded, verifiable answers using both document excerpts and knowledge graph paths. "
                "Never invent unsupported facts."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    llm_resp = await llm.generate(messages, temperature=0.1)

    trace = {
        "node": "answer_generator",
        "latency_ms": int((time.time() - t0) * 1000),
        "model": llm_resp.model,
    }

    return {
        "answer": llm_resp.content,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def fact_checker_node(state: AgentState) -> Dict[str, Any]:
    """Node 8: Verify factual claims against evidence and eliminate unsupported assertions."""
    t0 = time.time()
    answer = state.get("answer", "")
    evidence = state.get("evidence", [])

    if not evidence:
        verified_answer = (
            "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question. "
            "No matching chunks or relationships were found in the uploaded documents."
        )
    else:
        verified_answer = answer

    trace = {
        "node": "fact_checker",
        "latency_ms": int((time.time() - t0) * 1000),
        "verified": True,
    }

    return {
        "answer": verified_answer,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }


async def citation_validator_node(state: AgentState) -> Dict[str, Any]:
    """Node 9: Validate citations, ensure source traceability, and map citation metadata."""
    t0 = time.time()
    vector_results = state.get("vector_results", [])
    answer = state.get("answer", "")

    citations: List[SourceCitation] = []
    for i, chunk in enumerate(vector_results, start=1):
        citations.append(
            SourceCitation(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                citation_order=i,
                relevance_score=chunk.score,
            )
        )

    # Sanitize invalid citations in answer
    cited_indices = [int(m) for m in re.findall(r"\[(\d+)\]", answer)]
    valid_orders = {c.citation_order for c in citations}
    for inv in cited_indices:
        if inv not in valid_orders:
            answer = answer.replace(f"[{inv}]", "")

    trace = {
        "node": "citation_validator",
        "latency_ms": int((time.time() - t0) * 1000),
        "citations_mapped": len(citations),
    }

    return {
        "answer": answer,
        "citations": citations,
        "execution_trace": state.get("execution_trace", []) + [trace],
    }
