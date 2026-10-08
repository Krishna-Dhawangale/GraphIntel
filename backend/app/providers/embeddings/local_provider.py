import hashlib
import math
from typing import List

from app.providers.embeddings.base import EmbeddingProvider


class LocalDeterministicEmbeddingProvider(EmbeddingProvider):
    """Fast, deterministic, normalized embedding provider for local dev, offline environments, and tests."""

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dim
        words = text.lower().split()
        if not words:
            return vec

        for word in words:
            # Hash word to multiple dimensions to create semantic projection
            h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
            for i in range(4):
                slot = (h + i * 997) % self._dim
                sign = 1.0 if ((h >> (i * 4)) & 1) == 1 else -1.0
                vec[slot] += sign

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]
