"""Format extraction results as clean Markdown."""

from __future__ import annotations

from kiku.extractor import ExtractionResult
from kiku.parser import Block


def format_results(result: ExtractionResult) -> str:
    """Render extraction results as a Markdown document."""
    lines: list[str] = []

    # Header
    lines.append(f"# Kiku Extraction: {result.profile_name}")
    lines.append("")
    lines.append(f"**Profile:** {result.profile_name}")
    lines.append(f"**Description:** {result.profile_description}")
    lines.append(f"**Total blocks:** {result.total_blocks}")
    lines.append(f"**Response blocks:** {result.response_blocks}")
    lines.append(
        f"**Matches:** {len(result.matches)} "
        f"({result.regex_matches} regex, {result.semantic_matches} semantic)"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Matches
    for i, match in enumerate(result.matches, 1):
        lines.append(f"## Match {i} [{match.tier}]")
        lines.append("")
        lines.append(f"*{match.reason}*")
        lines.append("")

        # Context before
        for ctx_block in match.context_before:
            lines.append(_format_context_block(ctx_block))
            lines.append("")

        # The matched block itself
        lines.append(_format_matched_block(match.block))
        lines.append("")

        # Context after
        for ctx_block in match.context_after:
            lines.append(_format_context_block(ctx_block))
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def _format_matched_block(block: Block) -> str:
    """Format the matched block with emphasis."""
    header = _block_header(block)
    # Wrap content in a blockquote to visually distinguish
    quoted = "\n".join(f"> {line}" for line in block.content.split("\n"))
    return f"**>>> {header}**\n\n{quoted}"


def _format_context_block(block: Block) -> str:
    """Format a context block (before/after the match)."""
    header = _block_header(block)
    # Truncate long context blocks
    content = block.content
    if len(content) > 500:
        content = content[:500] + "\n[...truncated...]"
    return f"*{header}*\n\n{content}"


def _block_header(block: Block) -> str:
    """Build a header string for a block."""
    label = block.block_type.upper()
    ts = f" ({block.timestamp})" if block.timestamp else ""
    return f"[{label} #{block.index}]{ts}"
