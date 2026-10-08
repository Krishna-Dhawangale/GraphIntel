from typing import List

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.embeddings.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIMENSION or 1536
        self.client = AsyncOpenAI(api_key=self.api_key)

    @property
    def dimension(self) -> int:
        return self._dim

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Batch in maximum batches of 100
        batch_size = 100
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            # Replace empty strings
            cleaned_batch = [t.strip() or " " for t in batch]
            response = await self.client.embeddings.create(
                input=cleaned_batch,
                model=self.model,
            )
            # Ensure sort order by index
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in sorted_data])

        return all_embeddings
