"""
Ollama LLM Provider — migrated from direct ollama.chat() calls in agents.py.
Supports structured output with json.loads() + Pydantic (replaces eval()).
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

# Prompt version for observability
PROMPT_VERSION = "v1"


class OllamaProvider(BaseLLMProvider):
    """
    Ollama LLM provider.
    Replaces direct `ollama.chat()` calls scattered throughout agents.py.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.model = model or settings.LLM_MODEL
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS

    def _build_messages(self, prompt: str, system: str | None) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Call Ollama chat API and return the text response."""
        messages = self._build_messages(prompt, system)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": self.max_tokens,
                        },
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"].strip()
        except httpx.TimeoutException as exc:
            raise LLMProviderError(f"Ollama request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Ollama HTTP error: {exc}") from exc
        except KeyError as exc:
            raise LLMProviderError(f"Unexpected Ollama response format: {exc}") from exc

    async def structured_generate(
        self,
        prompt: str,
        output_schema: type[T],
        system: str | None = None,
        max_retries: int = 3,
    ) -> T:
        """
        Generate structured output validated against a Pydantic schema.

        On validation failure, appends the error to the prompt and retries.
        CRITICAL: Uses json.loads() only — never eval() — fixing the
        security vulnerability in the original agents.py line 185.
        """
        schema_json = json.dumps(output_schema.model_json_schema(), indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON that matches this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do not include any explanation or text outside the JSON block."
        )

        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                text = await self.generate(structured_prompt, system)
                result = self._parse_structured(text, output_schema)
                logger.debug(
                    "Structured generation succeeded",
                    schema=output_schema.__name__,
                    attempt=attempt,
                )
                return result
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "Structured output validation failed",
                    schema=output_schema.__name__,
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(exc),
                )
                # Add repair instruction to next attempt
                structured_prompt = (
                    f"{structured_prompt}\n\n"
                    f"Previous attempt failed with: {exc}\n"
                    f"Fix the JSON and try again."
                )

        raise LLMOutputValidationError(
            f"Failed to produce valid {output_schema.__name__} after {max_retries} attempts",
            details={"last_error": str(last_error)},
        )

    async def health_check(self) -> bool:
        """Return True if Ollama server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
