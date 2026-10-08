import math
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel


class RetrievalMetrics(BaseModel):
    recall_at_k: float
    precision_at_k: float
    mrr: float
    ndcg_at_k: float
    hit_rate: float
    k: int


class AnswerQualityMetrics(BaseModel):
    faithfulness: float
    answer_relevance: float
    context_relevance: float
    citation_accuracy: float
    citation_completeness: float
    entity_accuracy: float
    relationship_accuracy: float
    temporal_accuracy: float


def compute_recall_at_k(retrieved_items: List[str], ground_truth_items: List[str], k: int = 10) -> float:
    """Recall@K = |Retrieved[:K] ∩ GroundTruth| / |GroundTruth|"""
    if not ground_truth_items:
        return 1.0 if not retrieved_items else 0.0
    top_k = retrieved_items[:k]
    matched = set(top_k).intersection(set(ground_truth_items))
    return round(len(matched) / len(ground_truth_items), 4)


def compute_precision_at_k(retrieved_items: List[str], ground_truth_items: List[str], k: int = 10) -> float:
    """Precision@K = |Retrieved[:K] ∩ GroundTruth| / K"""
    top_k = retrieved_items[:k]
    if not top_k:
        return 0.0
    matched = set(top_k).intersection(set(ground_truth_items))
    return round(len(matched) / len(top_k), 4)


def compute_mrr(retrieved_items: List[str], ground_truth_items: List[str]) -> float:
    """Mean Reciprocal Rank: 1 / rank of first relevant item."""
    gt_set = set(ground_truth_items)
    for idx, item in enumerate(retrieved_items, start=1):
        if item in gt_set:
            return round(1.0 / idx, 4)
    return 0.0


def compute_ndcg_at_k(retrieved_items: List[str], ground_truth_items: List[str], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at rank K."""
    top_k = retrieved_items[:k]
    if not top_k or not ground_truth_items:
        return 0.0

    gt_set = set(ground_truth_items)
    dcg = 0.0
    for idx, item in enumerate(top_k, start=1):
        rel = 1.0 if item in gt_set else 0.0
        dcg += rel / math.log2(idx + 1)

    # Ideal DCG
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, min(len(gt_set), k) + 1))
    if idcg == 0.0:
        return 0.0
    return round(dcg / idcg, 4)


def compute_hit_rate(retrieved_items: List[str], ground_truth_items: List[str], k: int = 10) -> float:
    """Hit Rate@K: 1 if at least one relevant item appears in top K, else 0."""
    top_k = retrieved_items[:k]
    gt_set = set(ground_truth_items)
    return 1.0 if any(item in gt_set for item in top_k) else 0.0


def evaluate_retrieval(
    retrieved_items: List[str], ground_truth_items: List[str], k: int = 10
) -> RetrievalMetrics:
    """Compute all standard information retrieval metrics."""
    return RetrievalMetrics(
        recall_at_k=compute_recall_at_k(retrieved_items, ground_truth_items, k),
        precision_at_k=compute_precision_at_k(retrieved_items, ground_truth_items, k),
        mrr=compute_mrr(retrieved_items, ground_truth_items),
        ndcg_at_k=compute_ndcg_at_k(retrieved_items, ground_truth_items, k),
        hit_rate=compute_hit_rate(retrieved_items, ground_truth_items, k),
        k=k,
    )


def evaluate_faithfulness(answer: str, context: str, is_insufficient_expected: bool = False) -> float:
    """
    Evaluates whether facts stated in the answer are supported by the retrieved context.
    If insufficient evidence is expected and the answer states so, score is 1.0.
    """
    if "insufficient evidence" in answer.lower():
        return 1.0 if is_insufficient_expected else 0.3

    if not context or context.strip() == "":
        return 0.0

    # Token/term groundedness check
    answer_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", answer)]
    if not answer_words:
        return 1.0

    context_lower = context.lower()
    supported = sum(1 for w in answer_words if w in context_lower)
    return round(supported / len(answer_words), 4)


def evaluate_citation_accuracy(answer: str, valid_source_count: int) -> float:
    """
    Evaluates whether all cited references [X] in the answer map to actual retrieved sources.
    """
    citations = [int(m) for m in re.findall(r"\[(\d+)\]", answer)]
    if not citations:
        # If no citations were used, check if the answer is an insufficient evidence response
        return 1.0 if "insufficient evidence" in answer.lower() else 0.5

    valid_cits = [c for c in citations if 1 <= c <= valid_source_count]
    return round(len(valid_cits) / len(citations), 4)


def evaluate_entity_accuracy(answer: str, ground_truth_entities: List[str]) -> float:
    """
    Evaluates recall of ground-truth entities in the answer.
    """
    if not ground_truth_entities:
        return 1.0

    ans_lower = answer.lower()
    found = sum(1 for e in ground_truth_entities if e.lower() in ans_lower)
    return round(found / len(ground_truth_entities), 4)


def evaluate_relationship_accuracy(
    found_paths_or_relations: List[Dict[str, str]], ground_truth_relations: List[Dict[str, str]]
) -> float:
    """
    Evaluates precision/recall of relationship triples traversed or identified.
    """
    if not ground_truth_relations:
        return 1.0

    if not found_paths_or_relations:
        return 0.0

    # Normalize relations
    matched = 0
    for gt in ground_truth_relations:
        gt_src = gt.get("source", "").lower()
        gt_type = gt.get("type", "").lower()
        gt_tgt = gt.get("target", "").lower()
        for found in found_paths_or_relations:
            f_src = str(found.get("source", "")).lower()
            f_type = str(found.get("type", "")).lower()
            f_tgt = str(found.get("target", "")).lower()
            if (gt_src in f_src and gt_tgt in f_tgt) or (gt_type in f_type and gt_tgt in f_tgt):
                matched += 1
                break

    return round(matched / len(ground_truth_relations), 4)


def evaluate_temporal_accuracy(
    answer: str, expected_year: Optional[int], requires_temporal: bool
) -> float:
    """
    Evaluates adherence to temporal constraints.
    """
    if not requires_temporal or expected_year is None:
        return 1.0

    return 1.0 if str(expected_year) in answer else 0.2
