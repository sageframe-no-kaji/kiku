"""The Block data model — the unit a parser produces inside a Conversation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Block:
    """A single prompt or response block from a conversation."""

    block_type: str  # "prompt" or "response"
    timestamp: str
    content: str
    index: int
    raw_header: str = ""

    # Set during extraction — which tier matched and why
    match_tier: str | None = field(default=None, repr=False)
    match_reason: str | None = field(default=None, repr=False)
