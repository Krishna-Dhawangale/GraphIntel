from abc import ABC, abstractmethod
from typing import List, Tuple
from app.core.config import settings
from app.schemas.query import EvidenceItem, RetrievedChunk


class BaseReranker(ABC):
    """Abstract interface for evidence rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        evidence_items: List[EvidenceItem],
        top_k: int = 10,
    ) -> List[EvidenceItem]:
        """Rerank and filter evidence items."""
        pass


class SimpleFusionReranker(BaseReranker):
    """
    Weighted Evidence Fusion and Reranking.
    Normalizes scores across vector and graph modalities:
    - vector similarity
    - graph relationship confidence
    - token/keyword match with query
    """

    def __init__(self, vector_weight: float = 0.5, graph_weight: float = 0.5):
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight

    def rerank(
        self,
        query: str,
        evidence_items: List[EvidenceItem],
        top_k: int = 10,
    ) -> List[EvidenceItem]:
        if not evidence_items:
            return []

        query_tokens = set(query.lower().split())

        scored_items: List[Tuple[float, EvidenceItem]] = []
        for item in evidence_items:
            base_score = item.confidence

            # Compute term overlap boost
            content_tokens = set(item.content.lower().split())
            overlap = len(query_tokens.intersection(content_tokens)) / max(len(query_tokens), 1)

            if item.type == "graph":
                final_score = (base_score * self.graph_weight) + (overlap * 0.5)
            elif item.type == "vector":
                final_score = (base_score * self.vector_weight) + (overlap * 0.5)
            else:
                final_score = base_score * 0.4 + (overlap * 0.5)

            scored_items.append((final_score, item))

        # Sort descending by fused score
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored_items[:top_k]]


class CohereReranker(BaseReranker):
    """
    Production Cohere Rerank v3.5 cross-encoder integration with graceful fallback.
    """

    def __init__(self, api_key: str = "", model: str = "rerank-v3.5"):
        self.api_key = api_key or getattr(settings, "COHERE_API_KEY", "")
        self.model = model or getattr(settings, "COHERE_RERANK_MODEL", "rerank-v3.5")
        self._fallback = SimpleFusionReranker()

    def rerank(
        self,
        query: str,
        evidence_items: List[EvidenceItem],
        top_k: int = 10,
    ) -> List[EvidenceItem]:
        if not evidence_items or not self.api_key:
            return self._fallback.rerank(query, evidence_items, top_k)

        import httpx
        from app.core.logging import logger

        try:
            doc_texts = [item.content for item in evidence_items]
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "query": query,
                "documents": doc_texts,
                "top_n": min(top_k, len(evidence_items)),
            }
            # Cohere v2 rerank endpoint
            with httpx.Client(timeout=10.0) as client:
                resp = client.post("https://api.cohere.com/v2/rerank", json=payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                reranked_items = []
                for res in results:
                    idx = res.get("index")
                    if idx is not None and idx < len(evidence_items):
                        item = evidence_items[idx]
                        item.confidence = float(res.get("relevance_score", item.confidence))
                        reranked_items.append(item)
                return reranked_items or evidence_items[:top_k]
            else:
                logger.warning(
                    f"Cohere rerank returned HTTP {resp.status_code}. "
                    f"Falling back gracefully to SimpleFusionReranker."
                )
                return self._fallback.rerank(query, evidence_items, top_k)

        except Exception as e:
            logger.warning(f"Cohere reranker error ({e}). Falling back to SimpleFusionReranker.")
            return self._fallback.rerank(query, evidence_items, top_k)


class PassthroughReranker(BaseReranker):
    def rerank(
        self,
        query: str,
        evidence_items: List[EvidenceItem],
        top_k: int = 10,
    ) -> List[EvidenceItem]:
        return evidence_items[:top_k]


def get_reranker() -> BaseReranker:
    """Factory to retrieve configured reranker."""
    provider = getattr(settings, "RERANKER_PROVIDER", "simple").lower()
    cohere_key = getattr(settings, "COHERE_API_KEY", "")
    if provider == "cohere" or cohere_key:
        return CohereReranker()
    elif provider == "none":
        return PassthroughReranker()
    return SimpleFusionReranker()
