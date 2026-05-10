"""
Anthropic data export parser for Kiku.

Adapted from shuji.parsers.anthropic (Shodō). Kiku doesn't model artifacts
or separate thinking blocks; this parser uses the export's pre-concatenated
`text` field directly, consistent with how kiku.parsers.claude_markdown
strips thinking from response content.

Export shape (verified against real export, 2026-05-09):
- ZIP archive with conversations.json at root
- conversations.json: list of conversation dicts
- conversation.uuid, name, created_at, chat_messages
- message.uuid, sender ("human"|"assistant"), text, created_at
- message.content: list of typed blocks; thinking blocks excluded from `text`
"""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from kiku.parsers import Conversation
from kiku.parsers.block import Block

_BLOCK_TYPE_MAP: dict[str, str] = {
    "human": "prompt",
    "assistant": "response",
}


class AnthropicParser:
    """Parses Anthropic data exports (ZIP containing conversations.json)."""

    SOURCE = "anthropic"

    def can_parse(self, path: Path) -> bool:
        """Return True if `path` is a ZIP containing conversations.json."""
        if not path.is_file() or path.suffix.lower() != ".zip":
            return False
        try:
            with zipfile.ZipFile(path) as zf:
                return "conversations.json" in zf.namelist()
        except zipfile.BadZipFile:
            return False

    def parse(self, path: Path) -> Iterator[Conversation]:
        """Yield Conversation instances lazily from the export ZIP."""
        with zipfile.ZipFile(path) as zf, zf.open("conversations.json") as f:
            data: list[dict[str, Any]] = json.load(f)
        for raw_conv in data:
            yield self._build_conversation(raw_conv)

    def _build_conversation(self, raw: dict[str, Any]) -> Conversation:
        chat_messages = raw.get("chat_messages", [])
        blocks = [self._build_block(m, i) for i, m in enumerate(chat_messages)]
        return Conversation(
            id=raw["uuid"],
            name=raw.get("name") or None,
            blocks=blocks,
        )

    def _build_block(self, raw: dict[str, Any], index: int) -> Block:
        sender = raw["sender"]
        block_type = _BLOCK_TYPE_MAP.get(sender)
        if block_type is None:
            raise ValueError(f"Unknown sender {sender!r} at message index {index}")
        return Block(
            block_type=block_type,
            timestamp=str(raw.get("created_at", "")),
            content=raw.get("text", ""),
            index=index,
        )
