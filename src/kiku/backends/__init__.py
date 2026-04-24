"""LLM backends for semantic classification."""

from __future__ import annotations

import os
from typing import Protocol


class ClassifierBackend(Protocol):
    """Protocol for LLM classification backends."""

    def classify(self, text: str, prompt: str, model: str) -> tuple[bool, str]:
        """Classify a block of text against a semantic prompt.

        Returns:
            Tuple of (is_match, justification).
        """
        ...


def get_backend() -> ClassifierBackend:
    """Get the configured LLM backend.

    Backend selection:
        KIKU_BACKEND=anthropic (default) — uses Anthropic SDK
        KIKU_BACKEND=openai — uses OpenAI-compatible API (Ollama, LM Studio, etc.)
    """
    backend_name = os.environ.get("KIKU_BACKEND", "anthropic").lower()

    if backend_name == "openai":
        from kiku.backends.openai_compat import OpenAICompatBackend

        return OpenAICompatBackend()
    else:
        from kiku.backends.anthropic_backend import AnthropicBackend

        return AnthropicBackend()
