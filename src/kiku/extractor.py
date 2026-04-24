"""Core extraction engine — regex + semantic classification."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

from kiku.backends import ClassifierBackend
from kiku.parser import Block
from kiku.profile import ExtractionProfile


@dataclass
class ExtractionResult:
    """Results from an extraction run."""

    profile_name: str
    profile_description: str
    total_blocks: int
    response_blocks: int
    regex_matches: int
    semantic_matches: int
    matches: list[MatchedBlock]


@dataclass
class MatchedBlock:
    """A block that matched the extraction profile, with context."""

    block: Block
    tier: str  # "regex" or "semantic"
    reason: str  # matched pattern or LLM justification
    context_before: list[Block]
    context_after: list[Block]


def extract(
    blocks: list[Block],
    profile: ExtractionProfile,
    backend: ClassifierBackend | None = None,
    skip_semantic: bool = False,
) -> ExtractionResult:
    """Run extraction against a list of blocks using the given profile.

    The extraction runs in two tiers:
    1. Regex: match patterns from the profile against all blocks
    2. Semantic: send unmatched response blocks to LLM for classification
    """
    matched_indices: set[int] = set()
    matches: list[MatchedBlock] = []

    # Count response blocks
    response_blocks = sum(1 for b in blocks if b.block_type == "response")

    # --- Tier 1: Regex ---
    compiled_patterns = _compile_patterns(profile.patterns)
    for block in blocks:
        for pattern, raw in compiled_patterns:
            if pattern.search(block.content):
                matched_indices.add(block.index)
                ctx_before, ctx_after = _get_context(
                    blocks, block.index, profile.context_window
                )
                matches.append(
                    MatchedBlock(
                        block=block,
                        tier="regex",
                        reason=f"Pattern: {raw}",
                        context_before=ctx_before,
                        context_after=ctx_after,
                    )
                )
                break  # one match per block is enough

    regex_match_count = len(matches)

    # --- Tier 2: Semantic ---
    semantic_match_count = 0
    if not skip_semantic and backend is not None and profile.semantic_prompt:
        # Only classify response blocks that regex didn't already catch
        unmatched_responses = [
            b
            for b in blocks
            if b.block_type == "response"
            and b.index not in matched_indices
            and len(b.content.strip()) > 20  # skip trivially short blocks
        ]

        total = len(unmatched_responses)
        for i, block in enumerate(unmatched_responses):
            _progress(i + 1, total, "Semantic pass")
            try:
                is_match, justification = backend.classify(
                    block.content, profile.semantic_prompt, profile.model
                )
            except Exception as e:
                _progress_clear()
                print(f"  Warning: semantic pass failed on block {block.index}: {e}")
                continue

            if is_match:
                matched_indices.add(block.index)
                ctx_before, ctx_after = _get_context(
                    blocks, block.index, profile.context_window
                )
                matches.append(
                    MatchedBlock(
                        block=block,
                        tier="semantic",
                        reason=justification,
                        context_before=ctx_before,
                        context_after=ctx_after,
                    )
                )
                semantic_match_count += 1

        _progress_clear()

    # Sort matches by block index (chronological)
    matches.sort(key=lambda m: m.block.index)

    return ExtractionResult(
        profile_name=profile.name,
        profile_description=profile.description,
        total_blocks=len(blocks),
        response_blocks=response_blocks,
        regex_matches=regex_match_count,
        semantic_matches=semantic_match_count,
        matches=matches,
    )


def _compile_patterns(
    patterns: list[str],
) -> list[tuple[re.Pattern[str], str]]:
    """Compile regex patterns, case-insensitive."""
    compiled: list[tuple[re.Pattern[str], str]] = []
    for raw in patterns:
        try:
            compiled.append((re.compile(raw, re.IGNORECASE), raw))
        except re.error as e:
            print(f"  Warning: invalid pattern '{raw}': {e}")
    return compiled


def _get_context(
    blocks: list[Block], index: int, window: int
) -> tuple[list[Block], list[Block]]:
    """Get context blocks before and after a given block index."""
    # Find position in the blocks list
    pos = next((i for i, b in enumerate(blocks) if b.index == index), None)
    if pos is None:
        return [], []

    before = blocks[max(0, pos - window) : pos]
    after = blocks[pos + 1 : pos + 1 + window]
    return before, after


def _progress(current: int, total: int, label: str) -> None:
    """Print a progress indicator."""
    sys.stderr.write(f"\r  {label}: {current}/{total}")
    sys.stderr.flush()


def _progress_clear() -> None:
    """Clear the progress line."""
    sys.stderr.write("\r" + " " * 60 + "\r")
    sys.stderr.flush()
