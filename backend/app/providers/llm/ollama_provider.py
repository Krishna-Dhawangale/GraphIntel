from typing import Dict, List

import httpx

from app.core.config import settings
from app.core.exceptions import InternalServerErrorException
from app.core.logging import logger
from app.providers.llm.base import LLMProvider, LLMResponse


class OllamaLLMProvider(LLMProvider):
    def __init__(self, host: str = "", model: str = ""):
        self.host = host or settings.OLLAMA_HOST
        self.model = model or settings.OLLAMA_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        url = f"{self.host.rstrip('/')}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return LLMResponse(
                    content=content,
                    model=self.model,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                )
        except Exception as e:
            logger.error(f"Ollama completion error: {e}")
            raise InternalServerErrorException(f"Ollama connection error: {str(e)}")
