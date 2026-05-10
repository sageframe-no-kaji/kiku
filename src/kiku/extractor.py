"""Core extraction engine — regex + semantic classification."""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass

from kiku.backends import ClassifierBackend
from kiku.parsers import Conversation
from kiku.parsers.block import Block
from kiku.profile import ExtractionProfile

# Skip trivially short responses like "OK." / "Sure."
_MIN_SEMANTIC_CHARS = 20


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
    conversations_count: int = 1


@dataclass
class MatchedBlock:
    """A block that matched the extraction profile, with context."""

    block: Block
    tier: str  # "regex" or "semantic"
    reason: str  # matched pattern or LLM justification
    context_before: list[Block]
    context_after: list[Block]
    conversation_id: str = ""
    conversation_name: str | None = None


def extract(
    conversation: Conversation,
    profile: ExtractionProfile,
    backend: ClassifierBackend | None = None,
    skip_semantic: bool = False,
) -> ExtractionResult:
    """Run extraction against a Conversation using the given profile.

    The extraction runs in two tiers:
    1. Regex: match patterns from the profile against all blocks
    2. Semantic: send unmatched response blocks to LLM for classification
    """
    blocks = conversation.blocks
    matched_indices: set[int] = set()
    matches: list[MatchedBlock] = []

    # Count response blocks
    response_blocks = sum(1 for b in blocks if b.block_type == "response")

    # --- Tier 1: Regex ---
    compiled_patterns = _compile_patterns(profile.patterns)
    for block in blocks:
        if not _block_matches_target(block, profile.target):
            continue
        hit_patterns = [
            raw for pattern, raw in compiled_patterns if pattern.search(block.content)
        ]
        if hit_patterns:
            matched_indices.add(block.index)
            ctx_before, ctx_after = _get_context(
                blocks, block.index, profile.context_window
            )
            if len(hit_patterns) == 1:
                reason = f"Pattern: {hit_patterns[0]}"
            else:
                reason = f"Patterns: {', '.join(hit_patterns)}"
            matches.append(
                MatchedBlock(
                    block=block,
                    tier="regex",
                    reason=reason,
                    context_before=ctx_before,
                    context_after=ctx_after,
                    conversation_id=conversation.id,
                    conversation_name=conversation.name,
                )
            )

    regex_match_count = len(matches)

    # --- Tier 2: Semantic ---
    semantic_match_count = 0
    if not skip_semantic and backend is not None and profile.semantic_prompt:
        # Classify target-matching blocks that regex didn't already catch
        candidates = [
            b
            for b in blocks
            if _block_matches_target(b, profile.target)
            and b.index not in matched_indices
            and len(b.content.strip()) > _MIN_SEMANTIC_CHARS
        ]

        total = len(candidates)
        for i, block in enumerate(candidates):
            _progress(i + 1, total, "Semantic pass")
            prior = _prior_block(blocks, block.index)
            context_before = prior.content if prior else None
            try:
                is_match, justification = backend.classify(
                    block.content,
                    profile.semantic_prompt,
                    profile.model,
                    context_before=context_before,
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
                        conversation_id=conversation.id,
                        conversation_name=conversation.name,
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


def extract_corpus(
    conversations: Iterable[Conversation],
    profile: ExtractionProfile,
    backend: ClassifierBackend | None = None,
    skip_semantic: bool = False,
) -> ExtractionResult:
    """Run extraction across many conversations, aggregating into one result.

    Per-conversation matches stay in the order `extract()` produces them
    (chronological by block index); across conversations, order follows
    iteration order.
    """
    all_matches: list[MatchedBlock] = []
    total_blocks = 0
    total_response_blocks = 0
    regex_count = 0
    semantic_count = 0
    convs_seen = 0

    for conv in conversations:
        convs_seen += 1
        per = extract(conv, profile, backend=backend, skip_semantic=skip_semantic)
        all_matches.extend(per.matches)
        total_blocks += per.total_blocks
        total_response_blocks += per.response_blocks
        regex_count += per.regex_matches
        semantic_count += per.semantic_matches

    return ExtractionResult(
        profile_name=profile.name,
        profile_description=profile.description,
        total_blocks=total_blocks,
        response_blocks=total_response_blocks,
        regex_matches=regex_count,
        semantic_matches=semantic_count,
        matches=all_matches,
        conversations_count=convs_seen,
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


def _block_matches_target(block: Block, target: str) -> bool:
    """Return True if the block's type matches the profile's target."""
    if target == "both":
        return True
    return block.block_type == target


def _prior_block(blocks: list[Block], index: int) -> Block | None:
    """Return the block immediately before the given block index, or None."""
    pos = next((i for i, b in enumerate(blocks) if b.index == index), None)
    if pos is None or pos == 0:
        return None
    return blocks[pos - 1]


def _progress(current: int, total: int, label: str) -> None:
    """Print a progress indicator."""
    sys.stderr.write(f"\r  {label}: {current}/{total}")
    sys.stderr.flush()


def _progress_clear() -> None:
    """Clear the progress line."""
    sys.stderr.write("\r" + " " * 60 + "\r")
    sys.stderr.flush()
