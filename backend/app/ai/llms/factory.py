"""
LLM Provider factory.
Returns the correct provider based on LLM_PROVIDER environment variable.
Business logic imports from here, never directly from provider modules.
"""
from functools import lru_cache

from app.ai.llms.base import BaseLLMProvider
from app.core.config import settings
from app.core.exceptions import LLMProviderError


@lru_cache(maxsize=1)
def get_llm_provider() -> BaseLLMProvider:
    """
    Create and return the configured LLM provider singleton.
    Set LLM_PROVIDER env var to switch between: ollama, gemini, openai
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from app.ai.llms.ollama_provider import OllamaProvider
        return OllamaProvider()

    elif provider == "gemini":
        # TODO Phase 3+: Implement GeminiProvider
        raise LLMProviderError(
            "Gemini provider not yet implemented. Set LLM_PROVIDER=ollama for now."
        )

    elif provider == "openai":
        # TODO Phase 3+: Implement OpenAICompatibleProvider
        raise LLMProviderError(
            "OpenAI-compatible provider not yet implemented. Set LLM_PROVIDER=ollama for now."
        )

    else:
        raise LLMProviderError(
            f"Unknown LLM provider '{provider}'. Valid options: ollama, gemini, openai"
        )
