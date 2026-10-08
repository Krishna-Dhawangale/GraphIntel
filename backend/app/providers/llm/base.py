from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class LLMProvider(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate a completion response from the language model."""
        pass
