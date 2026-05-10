"""Tests for Markdown output formatting."""

from kiku.extractor import ExtractionResult, MatchedBlock
from kiku.formatter import format_results
from kiku.parsers.block import Block


def _make_result(
    matches: list[MatchedBlock] | None = None,
    regex_matches: int = 0,
    semantic_matches: int = 0,
) -> ExtractionResult:
    return ExtractionResult(
        profile_name="test_profile",
        profile_description="A test profile",
        total_blocks=8,
        response_blocks=4,
        regex_matches=regex_matches,
        semantic_matches=semantic_matches,
        matches=matches or [],
    )


def test_header_includes_profile_name() -> None:
    result = _make_result()
    output = format_results(result)
    assert "# Kiku Extraction: test_profile" in output


def test_header_includes_stats() -> None:
    result = _make_result()
    output = format_results(result)
    assert "**Total blocks:** 8" in output
    assert "**Response blocks:** 4" in output


def test_match_counts_in_header() -> None:
    result = _make_result(regex_matches=2, semantic_matches=1)
    output = format_results(result)
    assert "(2 regex, 1 semantic)" in output


def test_match_section_rendered() -> None:
    match = MatchedBlock(
        block=Block(
            block_type="response",
            timestamp="1:00",
            content="Go eat something.",
            index=1,
        ),
        tier="regex",
        reason="Pattern: go eat",
        context_before=[],
        context_after=[],
    )
    result = _make_result(matches=[match], regex_matches=1)
    output = format_results(result)
    assert "## Match 1 [regex]" in output
    assert "Pattern: go eat" in output
    assert "> Go eat something." in output


def test_context_blocks_rendered() -> None:
    before = Block(
        block_type="prompt", timestamp="0:59", content="What should I do?", index=0
    )
    matched = Block(
        block_type="response", timestamp="1:00", content="Go eat something.", index=1
    )
    after = Block(block_type="prompt", timestamp="1:01", content="Ok fine.", index=2)
    match = MatchedBlock(
        block=matched,
        tier="regex",
        reason="Pattern: go eat",
        context_before=[before],
        context_after=[after],
    )
    result = _make_result(matches=[match], regex_matches=1)
    output = format_results(result)
    assert "What should I do?" in output
    assert "Ok fine." in output


def test_long_context_truncated() -> None:
    long_content = "x" * 600
    ctx = Block(block_type="prompt", timestamp="0:59", content=long_content, index=0)
    matched = Block(block_type="response", timestamp="1:00", content="Go eat.", index=1)
    match = MatchedBlock(
        block=matched,
        tier="regex",
        reason="Pattern: go eat",
        context_before=[ctx],
        context_after=[],
    )
    result = _make_result(matches=[match], regex_matches=1)
    output = format_results(result)
    assert "[...truncated...]" in output


def test_empty_results() -> None:
    result = _make_result()
    output = format_results(result)
    assert "## Match" not in output
    assert "**Matches:** 0" in output


def test_semantic_tier_label() -> None:
    match = MatchedBlock(
        block=Block(
            block_type="response",
            timestamp="1:00",
            content="You should rest.",
            index=1,
        ),
        tier="semantic",
        reason="Expresses concern about wellbeing.",
        context_before=[],
        context_after=[],
    )
    result = _make_result(matches=[match], semantic_matches=1)
    output = format_results(result)
    assert "[semantic]" in output
    assert "Expresses concern" in output


def test_block_header_format() -> None:
    match = MatchedBlock(
        block=Block(
            block_type="response",
            timestamp="4/14/2026, 7:07 AM",
            content="Rest up.",
            index=3,
        ),
        tier="regex",
        reason="Pattern: rest",
        context_before=[],
        context_after=[],
    )
    result = _make_result(matches=[match], regex_matches=1)
    output = format_results(result)
    assert "RESPONSE #3" in output
    assert "4/14/2026, 7:07 AM" in output
