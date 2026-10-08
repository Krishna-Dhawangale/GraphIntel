from app.core.config import settings
from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.providers.embeddings.local_provider import LocalDeterministicEmbeddingProvider
from app.providers.embeddings.openai_provider import OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Factory to retrieve configured EmbeddingProvider."""
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiEmbeddingProvider()
    elif settings.EMBEDDING_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider()
    return LocalDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
