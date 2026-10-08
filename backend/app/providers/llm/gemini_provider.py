from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import InternalServerErrorException
from app.core.logging import logger
from app.providers.llm.base import LLMProvider, LLMResponse


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM provider using asynchronous HTTP requests."""

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model = model or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        # Ensure model doesn't have duplicate models/ prefix
        if self.model.startswith("models/"):
            self.model = self.model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        if not self.api_key:
            raise InternalServerErrorException("GEMINI_API_KEY is not configured.")

        # Separate system message and chat contents
        system_text = ""
        contents: List[Dict[str, Any]] = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_text = (system_text + "\n" + content).strip()
            elif role in ("assistant", "model"):
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        # If only system instruction was provided, ensure at least one user content exists
        if not contents and system_text:
            contents.append({"role": "user", "parts": [{"text": "Proceed."}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_text:
            payload["systemInstruction"] = {
                "parts": [{"text": system_text}]
            }

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code != 200:
                error_body = resp.text
                if resp.status_code == 429:
                    logger.warning("Gemini free tier rate limit exceeded (429). Falling back gracefully.")
                    from app.providers.llm.mock_provider import MockLLMProvider
                    mock = MockLLMProvider()
                    return await mock.generate(messages, temperature, max_tokens)

                logger.error(f"Gemini API returned status {resp.status_code}: {error_body}")
                raise InternalServerErrorException(
                    f"Gemini API error ({resp.status_code}): {error_body[:200]}"
                )

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning(f"Gemini returned no candidates: {data}")
                return LLMResponse(
                    content="Unable to generate response from Gemini.",
                    model=self.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            response_text = "".join(p.get("text", "") for p in parts)

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)

            return LLMResponse(
                content=response_text,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        except InternalServerErrorException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error calling Gemini API: {e}")
            raise InternalServerErrorException(f"Gemini LLM error: {str(e)}")
