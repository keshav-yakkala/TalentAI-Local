"""
Grok (xAI) LLM Provider — OpenAI-compatible REST interface.
Uses GROK_API_KEY from .env / settings.
"""
from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.ai.llms.base import BaseLLMProvider
from app.core.config import settings
from app.core.exceptions import LLMOutputValidationError, LLMProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class GrokProvider(BaseLLMProvider):
    """
    Grok (xAI) API LLM Provider.
    Calls https://api.x.ai/v1/chat/completions with Authorization header.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model or getattr(settings, "GROK_MODEL", "grok-2-latest")
        self.api_key = api_key or getattr(settings, "GROK_API_KEY", "")
        self.base_url = (base_url or getattr(settings, "GROK_BASE_URL", "https://api.x.ai/v1")).rstrip("/")
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_messages(self, prompt: str, system: str | None) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system: str | None = None) -> str:
        messages = self._build_messages(prompt, system)
        headers = self._build_headers()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise LLMProviderError(f"Grok API HTTP {resp.status_code}: {resp.text}")
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.RequestError as exc:
            logger.error("Grok connection error", error=str(exc))
            raise LLMProviderError(f"Grok host unreachable at {self.base_url}") from exc

    async def structured_generate(
        self,
        prompt: str,
        output_schema: type[T],
        system: str | None = None,
        max_retries: int = 3,
    ) -> T:
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        system_with_schema = (
            (system or "")
            + f"\n\nIMPORTANT: You must respond in valid JSON matching this schema:\n{schema_json}"
        )

        for attempt in range(1, max_retries + 1):
            raw_text = await self.generate(prompt, system=system_with_schema)
            json_text = self._extract_json(raw_text)

            try:
                data = json.loads(json_text)
                return output_schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "Grok structured output validation failed",
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt == max_retries:
                    raise LLMOutputValidationError(
                        f"Grok failed to produce valid {output_schema.__name__} after {max_retries} attempts."
                    ) from exc
                await asyncio.sleep(0.5)

        raise LLMOutputValidationError("Failed after max retries")

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=self._build_headers(),
                )
                return resp.status_code in (200, 400, 403)
        except Exception:
            return False
