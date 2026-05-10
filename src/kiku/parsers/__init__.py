"""Parser plugin registry for Kiku."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from kiku.parsers.block import Block


@dataclass
class Conversation:
    """A single conversation, the unit a Parser yields."""

    id: str
    name: str | None
    blocks: list[Block] = field(default_factory=list)


@runtime_checkable
class Parser(Protocol):
    """Contract every parser plugin must satisfy."""

    def can_parse(self, path: Path) -> bool:
        """Return True if this parser can handle the file at `path`."""
        ...

    def parse(self, path: Path) -> Iterator[Conversation]:
        """Parse the export at `path`, yielding Conversation instances lazily."""
        ...


from kiku.parsers.claude_markdown import ClaudeMarkdownParser  # noqa: E402

PARSERS: list[Parser] = [ClaudeMarkdownParser()]

__all__ = ["Block", "Conversation", "Parser", "PARSERS"]
