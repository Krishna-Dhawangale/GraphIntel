from app.core.config import settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider
from app.providers.llm.mock_provider import MockLLMProvider
from app.providers.llm.ollama_provider import OllamaLLMProvider
from app.providers.llm.openai_provider import OpenAILLMProvider


def get_llm_provider() -> LLMProvider:
    """Factory to retrieve configured LLMProvider."""
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMProvider()
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider()
    elif settings.LLM_PROVIDER == "ollama":
        return OllamaLLMProvider()
    elif settings.GEMINI_API_KEY and settings.LLM_PROVIDER != "openai":
        return GeminiLLMProvider()
    return MockLLMProvider()
