"""Parse exported AI conversations into structured blocks."""

from __future__ import annotations

import re
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


# Matches ## Prompt: or ## Response: headers with optional timestamp on next line
_BLOCK_HEADER = re.compile(
    r"^## (Prompt|Response):\s*$",
    re.MULTILINE,
)

_TIMESTAMP_LINE = re.compile(
    r"^\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?\s*$"
)

# Matches the thinking block that Claude wraps in code fences
_THINKING_BLOCK = re.compile(
    r"^````(?:plaintext)?\s*\n" r"Thought process:.*?" r"\n````\s*$",
    re.MULTILINE | re.DOTALL,
)


def parse_conversation(text: str) -> list[Block]:
    """Split a Claude.ai markdown export into prompt/response blocks.

    Expects the format:
        ## Prompt:
        <timestamp>
        <content>

        ## Response:
        <timestamp>
        <content>
    """
    blocks: list[Block] = []

    # Find all header positions
    headers = list(_BLOCK_HEADER.finditer(text))
    if not headers:
        return blocks

    for i, header_match in enumerate(headers):
        block_type = header_match.group(1).lower()
        raw_header = header_match.group(0)

        # Content extends from end of header to start of next header (or EOF)
        start = header_match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        raw_content = text[start:end].strip()

        # Extract timestamp from first non-empty line
        lines = raw_content.split("\n")
        timestamp = ""
        content_start = 0
        for j, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if _TIMESTAMP_LINE.match(stripped):
                timestamp = stripped
                content_start = j + 1
            break

        content = "\n".join(lines[content_start:]).strip()

        # Strip thinking blocks from responses
        if block_type == "response":
            content = _THINKING_BLOCK.sub("", content).strip()

        blocks.append(
            Block(
                block_type=block_type,
                timestamp=timestamp,
                content=content,
                index=i,
                raw_header=raw_header,
            )
        )

    return blocks
