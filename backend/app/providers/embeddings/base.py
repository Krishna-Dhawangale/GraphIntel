from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension of the generated embeddings."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a batch of text strings."""
        pass

    async def get_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for a single text string."""
        results = await self.get_embeddings([text])
        return results[0]
