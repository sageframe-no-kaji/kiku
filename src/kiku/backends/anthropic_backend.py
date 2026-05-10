"""Anthropic Claude backend for semantic classification."""

from __future__ import annotations

import os

import anthropic


class AnthropicBackend:
    """Classify text blocks using Claude via the Anthropic SDK."""

    def __init__(self) -> None:
        api_key = os.environ.get("KIKU_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set KIKU_API_KEY or ANTHROPIC_API_KEY to use the Anthropic backend"
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def classify(
        self,
        text: str,
        prompt: str,
        model: str,
        context_before: str | None = None,
    ) -> tuple[bool, str]:
        """Send a block to Claude for semantic classification.

        Returns:
            Tuple of (is_match, justification).
        """
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

        message = self._client.messages.create(
            model=model,
            max_tokens=150,
            messages=[{"role": "user", "content": user_content}],
        )

        response_text = message.content[0].text.strip()  # type: ignore[union-attr]
        return _parse_classification(response_text)


def _parse_classification(response: str) -> tuple[bool, str]:
    """Parse a YES/NO classification response."""
    lines = response.strip().split("\n", 1)
    first_line = lines[0].strip().upper()
    justification = lines[1].strip() if len(lines) > 1 else ""

    is_match = first_line.startswith("YES")
    return is_match, justification
