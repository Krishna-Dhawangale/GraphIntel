import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

from app.core.cost_tracker import cost_tracker
from app.evaluation.dataset import evaluation_dataset
from app.evaluation.metrics import (
    compute_hit_rate,
    compute_mrr,
    compute_ndcg_at_k,
    compute_precision_at_k,
    compute_recall_at_k,
    evaluate_citation_accuracy,
    evaluate_entity_accuracy,
    evaluate_faithfulness,
    evaluate_relationship_accuracy,
    evaluate_temporal_accuracy,
)
from app.evaluation.runner import EvaluationRunner
from app.main import app
from app.schemas.query import EvidenceItem, RetrievedChunk
from app.services.hybrid_retriever import HybridRetriever


def test_evaluation_dataset_structure():
    """Verify versioned evaluation dataset contains all 6 required categories."""
    assert len(evaluation_dataset.questions) >= 20
    categories = {q.category for q in evaluation_dataset.questions}
    expected_categories = {
        "factual",
        "relationship",
        "multihop",
        "temporal",
        "comparative",
        "insufficient_evidence",
    }
    assert expected_categories.issubset(categories)

    for q in evaluation_dataset.questions:
        assert q.id
        assert q.question
        assert q.expected_answer
        if q.category == "insufficient_evidence":
            assert q.expected_insufficient is True


def test_retrieval_metrics_calculation():
    """Verify Recall, Precision, MRR, NDCG, and Hit Rate against known ground truths."""
    gt = ["item1", "item2", "item3"]
    retrieved = ["item1", "item4", "item2", "item5", "item6"]

    # Recall@3: item1, item2 in top 3 -> 2/3 = 0.6667
    rec = compute_recall_at_k(retrieved, gt, k=3)
    assert rec == round(2 / 3, 4)

    # Recall@5: item1, item2 in top 5 -> 2/3 = 0.6667
    rec5 = compute_recall_at_k(retrieved, gt, k=5)
    assert rec5 == round(2 / 3, 4)

    # Precision@3: 2 matched in top 3 -> 2/3 = 0.6667
    prec = compute_precision_at_k(retrieved, gt, k=3)
    assert prec == round(2 / 3, 4)

    # MRR: first match at rank 1 -> 1.0
    mrr = compute_mrr(retrieved, gt)
    assert mrr == 1.0

    # NDCG@5
    ndcg = compute_ndcg_at_k(retrieved, gt, k=5)
    assert ndcg > 0.5

    # Hit Rate: at least one match
    hit = compute_hit_rate(retrieved, gt, k=3)
    assert hit == 1.0

    # No match scenario
    assert compute_hit_rate(["unrelated"], gt, k=3) == 0.0
    assert compute_mrr(["unrelated"], gt) == 0.0


def test_answer_quality_metrics():
    """Verify Faithfulness, Citation Accuracy, Entity, Relationship, and Temporal metrics."""
    # 1. Faithfulness
    context = "OpenAI was founded in 2015 in San Francisco."
    answer = "OpenAI was founded in 2015 in San Francisco."
    faith = evaluate_faithfulness(answer, context)
    assert faith >= 0.8

    # Insufficient evidence faithfulness
    insuf_ans = "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question."
    assert evaluate_faithfulness(insuf_ans, "", is_insufficient_expected=True) == 1.0

    # 2. Citation Accuracy
    cit_ans = "The firm generated $50B in revenue [1] and acquired startup [2]."
    assert evaluate_citation_accuracy(cit_ans, valid_source_count=2) == 1.0
    assert evaluate_citation_accuracy(cit_ans, valid_source_count=1) == 0.5  # [2] is invalid

    # 3. Entity Accuracy
    entities = ["DeepMind", "Demis Hassabis"]
    ans_with_entities = "Demis Hassabis was the co-founder of DeepMind."
    assert evaluate_entity_accuracy(ans_with_entities, entities) == 1.0

    # 4. Relationship Accuracy
    gt_rels = [{"source": "Google", "type": "ACQUIRED", "target": "DeepMind"}]
    found_rels = [{"source": "Google", "type": "ACQUIRED", "target": "DeepMind"}]
    assert evaluate_relationship_accuracy(found_rels, gt_rels) == 1.0

    # 5. Temporal Accuracy
    assert evaluate_temporal_accuracy("In 2023, the funding occurred.", expected_year=2023, requires_temporal=True) == 1.0
    assert evaluate_temporal_accuracy("The funding happened long ago.", expected_year=2023, requires_temporal=True) == 0.2


def test_cost_tracker_dynamic_pricing():
    """Verify cost tracker computes token costs correctly and supports dynamic pricing."""
    cost = cost_tracker.calculate_cost("gpt-4o", prompt_tokens=1000, completion_tokens=1000)
    # Default gpt-4o: 0.005 prompt + 0.015 completion per 1k = 0.020
    assert cost == 0.02

    # Dynamic pricing update
    cost_tracker.set_pricing("custom-model", prompt_cost_per_1k=0.01, completion_cost_per_1k=0.02)
    custom_cost = cost_tracker.calculate_cost("custom-model", prompt_tokens=500, completion_tokens=500)
    assert custom_cost == 0.015


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    """Verify GET /api/v1/metrics returns Prometheus formatted metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Hit an endpoint first to produce metrics
        await client.get("/api/v1/health")
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
        content = resp.text
        assert "graphintel_requests_total" in content
        assert "graphintel_request_duration_seconds" in content
        assert "graphintel_retrieval_latency_seconds" in content


@pytest.mark.asyncio
async def test_liveness_and_readiness_probes():
    """Verify /health/live and /health/ready endpoints for Kubernetes / production orchestration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live_resp = await client.get("/api/v1/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json()["status"] == "alive"

        ready_resp = await client.get("/api/v1/health/ready")
        assert ready_resp.status_code == 200
        assert ready_resp.json()["ready"] is True


@pytest.mark.asyncio
async def test_graceful_degradation_neo4j_down():
    """Test that if Neo4j graph retrieval fails, HybridRetriever degrades gracefully to vector-only."""
    mock_vector = MagicMock()
    mock_vector.retrieve = AsyncMock(
        return_value=[
            RetrievedChunk(
                chunk_id="chk-1",
                document_id="doc-1",
                filename="sec_filing.pdf",
                text="Acquisition details and financials",
                score=0.92,
            )
        ]
    )

    mock_graph = MagicMock()
    mock_graph.retrieve = AsyncMock(side_effect=ConnectionError("Neo4j cluster unavailable"))

    retriever = HybridRetriever(retrieval_service=mock_vector, graph_retriever=mock_graph)

    evidence, chunks, paths, entities, metrics = await retriever.retrieve(
        query="Acquisitions in 2024",
        user_id="test_user",
        retrieval_mode="hybrid",
    )

    assert len(chunks) == 1
    assert metrics["degraded"] is True
    assert "Neo4j cluster unavailable" in metrics["fallback_reason"]
    assert len(evidence) >= 1  # Vector evidence preserved


@pytest.mark.asyncio
async def test_graceful_degradation_vector_down():
    """Test that if Vector retrieval fails, HybridRetriever degrades gracefully to graph-only."""
    mock_vector = MagicMock()
    mock_vector.retrieve = AsyncMock(side_effect=TimeoutError("Qdrant search timed out"))

    mock_graph = MagicMock()
    mock_graph.retrieve = AsyncMock(
        return_value=(
            [EvidenceItem(type="graph", content="Google acquired DeepMind", confidence=1.0)],
            [],
            ["Google", "DeepMind"],
        )
    )

    retriever = HybridRetriever(retrieval_service=mock_vector, graph_retriever=mock_graph)

    evidence, chunks, paths, entities, metrics = await retriever.retrieve(
        query="Google acquired DeepMind",
        user_id="test_user",
        retrieval_mode="hybrid",
    )

    assert len(chunks) == 0
    assert metrics["degraded"] is True
    assert "Qdrant search timed out" in metrics["fallback_reason"]
    assert len(evidence) >= 1  # Graph evidence preserved


@pytest.mark.asyncio
async def test_evaluation_runner_benchmark():
    """Test that EvaluationRunner runs the benchmark suite and outputs the formatted comparison table."""
    sample_questions = evaluation_dataset.questions[:4]
    runner = EvaluationRunner(dataset=sample_questions)
    results = await runner.run_benchmark(user_id="test_runner")

    assert "vector" in results
    assert "hybrid" in results
    assert "agentic" in results

    table = runner.format_markdown_table(results)
    assert "| Metric | Basic RAG | GraphRAG | Agentic GraphRAG |" in table
    assert results["hybrid"].avg_recall_at_10 >= results["vector"].avg_recall_at_10
