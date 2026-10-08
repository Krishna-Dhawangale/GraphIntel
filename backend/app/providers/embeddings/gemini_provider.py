from typing import List
import httpx

from app.core.config import settings
from app.core.exceptions import InternalServerErrorException
from app.core.logging import logger
from app.providers.embeddings.base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini text embedding provider."""

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_EMBEDDING_MODEL", "text-embedding-004")
        if not self.model.startswith("models/"):
            self.model_path = f"models/{self.model}"
        else:
            self.model_path = self.model
        self._dim = 768
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def dimension(self) -> int:
        return self._dim

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise InternalServerErrorException("GEMINI_API_KEY is not configured.")

        all_embeddings: List[List[float]] = []
        batch_size = 50

        url = f"{self.base_url}/{self.model_path}:batchEmbedContents?key={self.api_key}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                requests_payload = [
                    {
                        "model": self.model_path,
                        "content": {"parts": [{"text": t.strip() or " "}]},
                    }
                    for t in batch
                ]

                try:
                    resp = await client.post(url, json={"requests": requests_payload})
                    if resp.status_code != 200:
                        logger.error(f"Gemini embedding returned status {resp.status_code}: {resp.text}")
                        raise InternalServerErrorException(
                            f"Gemini Embedding error ({resp.status_code}): {resp.text[:200]}"
                        )

                    data = resp.json()
                    embeddings_data = data.get("embeddings", [])
                    for emb in embeddings_data:
                        all_embeddings.append(emb.get("values", []))

                except Exception as e:
                    logger.exception(f"Error fetching embeddings from Gemini: {e}")
                    raise InternalServerErrorException(f"Gemini embedding error: {str(e)}")

        return all_embeddings
