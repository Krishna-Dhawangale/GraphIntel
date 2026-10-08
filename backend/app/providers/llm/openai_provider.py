from typing import Dict, List

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import InternalServerErrorException
from app.core.logging import logger
from app.providers.llm.base import LLMProvider, LLMResponse


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise InternalServerErrorException(f"LLM service error: {str(e)}")
