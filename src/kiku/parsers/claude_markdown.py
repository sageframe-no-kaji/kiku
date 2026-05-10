"""Parser for Claude.ai Markdown conversation exports."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

from kiku.parsers.block import Block
from kiku.preprocessor import strip_base64_images

if TYPE_CHECKING:
    from kiku.parsers import Conversation

# Matches ## Prompt: or ## Response: headers
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


class ClaudeMarkdownParser:
    """Parses Claude.ai Markdown conversation exports."""

    SOURCE = "claude_markdown"

    def can_parse(self, path: Path) -> bool:
        if not path.is_file() or path.suffix.lower() not in (".md", ".markdown"):
            return False
        try:
            head = path.read_text(encoding="utf-8", errors="ignore")[:8192]
        except OSError:
            return False
        return _BLOCK_HEADER.search(head) is not None

    def parse(self, path: Path) -> Iterator["Conversation"]:
        from kiku.parsers import Conversation

        raw_text = path.read_text(encoding="utf-8")
        text, original_size, stripped_size = strip_base64_images(raw_text)
        if stripped_size > 0:
            pct = (stripped_size / original_size) * 100
            print(
                f"  Stripped {stripped_size:,} bytes of base64 images ({pct:.0f}%)",
                file=sys.stderr,
            )
        blocks = _parse_blocks(text)
        yield Conversation(
            id=path.stem,
            name=path.stem,
            blocks=blocks,
        )


def _parse_blocks(text: str) -> list[Block]:
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

    headers = list(_BLOCK_HEADER.finditer(text))
    if not headers:
        return blocks

    for i, header_match in enumerate(headers):
        block_type = header_match.group(1).lower()
        raw_header = header_match.group(0)

        start = header_match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        raw_content = text[start:end].strip()

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
