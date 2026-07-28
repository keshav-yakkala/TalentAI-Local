"""
LLM Provider abstraction.
Business logic uses BaseLLMProvider only — never direct ollama.chat() calls.
Providers: OllamaProvider, GeminiProvider, OpenAICompatibleProvider
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate a text response for the given prompt."""
        ...

    @abstractmethod
    async def structured_generate(
        self,
        prompt: str,
        output_schema: type[T],
        system: str | None = None,
        max_retries: int = 3,
    ) -> T:
        """
        Generate a response and parse it into the given Pydantic model.
        Retries on validation failure up to max_retries times.
        Raises LLMOutputValidationError after exhausting retries.
        IMPORTANT: Never use eval() on LLM output. Always use json.loads() + Pydantic.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable."""
        ...

    def _extract_json(self, text: str) -> str:
        """
        Safely extract JSON from LLM response that may have markdown fences.
        Returns the raw JSON string for json.loads() — never eval().
        """
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        # Find the first { or [ 
        for i, ch in enumerate(text):
            if ch in ("{", "["):
                text = text[i:]
                break
        return text

    def _parse_structured(self, text: str, schema: type[T]) -> T:
        """
        Parse LLM output text into a Pydantic model.
        Uses json.loads(), NOT eval().
        """
        json_str = self._extract_json(text)
        data = json.loads(json_str)  # Safe — never eval()
        return schema.model_validate(data)
