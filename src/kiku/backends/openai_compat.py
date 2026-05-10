"""OpenAI-compatible backend for semantic classification (Ollama, LM Studio, etc.)."""

from __future__ import annotations

import os

import openai


class OpenAICompatBackend:
    """Classify text blocks using an OpenAI-compatible API."""

    def __init__(self) -> None:
        api_key = os.environ.get("KIKU_API_KEY", "ollama")
        api_base = os.environ.get("KIKU_API_BASE", "http://localhost:11434/v1")

        self._client = openai.OpenAI(api_key=api_key, base_url=api_base)

    def classify(
        self,
        text: str,
        prompt: str,
        model: str,
        context_before: str | None = None,
    ) -> tuple[bool, str]:
        """Send a block to the LLM for semantic classification.

        Returns:
            Tuple of (is_match, justification).
        """
        # For OpenAI-compatible backends, use the model from env if set
        effective_model = os.environ.get("KIKU_MODEL", model)

        if context_before is not None:
            user_content = (
                f"{prompt}\n\n"
                f"--- PRIOR MESSAGE ---\n{context_before}\n--- END PRIOR ---\n\n"
                f"--- TEXT TO CLASSIFY ---\n{text}\n--- END TEXT ---\n\n"
                "Respond with YES or NO on the first line, "
                "followed by a one-sentence justification."
            )
        else:
            user_content = (
                f"{prompt}\n\n"
                f"--- BEGIN TEXT ---\n{text}\n--- END TEXT ---\n\n"
                "Respond with YES or NO on the first line, "
                "followed by a one-sentence justification."
            )

        response = self._client.chat.completions.create(
            model=effective_model,
            max_tokens=150,
            messages=[{"role": "user", "content": user_content}],
        )

        response_text = (response.choices[0].message.content or "").strip()
        return _parse_classification(response_text)


def _parse_classification(response: str) -> tuple[bool, str]:
    """Parse a YES/NO classification response."""
    lines = response.strip().split("\n", 1)
    first_line = lines[0].strip().upper()
    justification = lines[1].strip() if len(lines) > 1 else ""

    is_match = first_line.startswith("YES")
    return is_match, justification
