"""Tests for the extraction engine."""

from kiku.extractor import extract
from kiku.parsers import Conversation
from kiku.parsers.block import Block
from kiku.profile import ExtractionProfile


def _conv(blocks: list[Block]) -> Conversation:
    return Conversation(id="t", name=None, blocks=blocks)


def _make_blocks() -> list[Block]:
    return [
        Block(
            block_type="prompt", timestamp="1:00", content="What should I do?", index=0
        ),
        Block(
            block_type="response",
            timestamp="1:01",
            content="Go eat something. You've been working all day.",
            index=1,
        ),
        Block(
            block_type="prompt",
            timestamp="1:02",
            content="Ok I'll keep going.",
            index=2,
        ),
        Block(
            block_type="response",
            timestamp="1:03",
            content="Here is the revised draft.",
            index=3,
        ),
        Block(block_type="prompt", timestamp="1:04", content="Ship it.", index=4),
        Block(
            block_type="response",
            timestamp="1:05",
            content="Go to bed. It's late.",
            index=5,
        ),
        Block(block_type="prompt", timestamp="1:06", content="Fine.", index=6),
        Block(
            block_type="response",
            timestamp="1:07",
            content="Good. Now go play with your daughter.",
            index=7,
        ),
    ]


def _make_profile() -> ExtractionProfile:
    return ExtractionProfile(
        name="test_caretaking",
        description="Test caretaking profile",
        patterns=["go eat", "go to bed", "play with your daughter"],
        semantic_prompt="",
        context_window=1,
    )


def test_regex_finds_matches() -> None:
    blocks = _make_blocks()
    profile = _make_profile()
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert result.regex_matches == 3
    assert result.semantic_matches == 0
    assert len(result.matches) == 3


def test_matches_are_chronological() -> None:
    blocks = _make_blocks()
    profile = _make_profile()
    result = extract(_conv(blocks), profile, skip_semantic=True)
    indices = [m.block.index for m in result.matches]
    assert indices == sorted(indices)


def test_context_window() -> None:
    blocks = _make_blocks()
    profile = _make_profile()
    result = extract(_conv(blocks), profile, skip_semantic=True)

    # First match (block 1) should have block 0 as context_before
    first = result.matches[0]
    assert len(first.context_before) == 1
    assert first.context_before[0].index == 0
    assert len(first.context_after) == 1
    assert first.context_after[0].index == 2


def test_match_tier_labeled() -> None:
    blocks = _make_blocks()
    profile = _make_profile()
    result = extract(_conv(blocks), profile, skip_semantic=True)
    for match in result.matches:
        assert match.tier == "regex"


def test_no_matches() -> None:
    blocks = _make_blocks()
    profile = ExtractionProfile(
        name="empty",
        description="no matches",
        patterns=["xyzzy_will_never_match"],
        semantic_prompt="",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 0


def test_case_insensitive() -> None:
    blocks = [
        Block(block_type="response", timestamp="1:00", content="GO EAT NOW.", index=0),
    ]
    profile = ExtractionProfile(
        name="case",
        description="case test",
        patterns=["go eat"],
        semantic_prompt="",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 1


def test_regex_pattern_with_alternation() -> None:
    blocks = [
        Block(
            block_type="response", timestamp="1:00", content="Get some rest.", index=0
        ),
        Block(
            block_type="response", timestamp="1:01", content="Get some sleep.", index=1
        ),
        Block(
            block_type="response", timestamp="1:02", content="Get some food.", index=2
        ),
    ]
    profile = ExtractionProfile(
        name="alternation",
        description="alternation test",
        patterns=["get some (rest|sleep)"],
        semantic_prompt="",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 2


def test_result_counts() -> None:
    blocks = _make_blocks()
    profile = _make_profile()
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert result.total_blocks == 8
    assert result.response_blocks == 4
    assert result.profile_name == "test_caretaking"


class FakeBackend:
    """Mock backend that classifies based on keyword."""

    def classify(
        self,
        text: str,
        prompt: str,
        model: str,
        context_before: str | None = None,
    ) -> tuple[bool, str]:
        if "working all day" in text.lower():
            return True, "Expresses concern about overwork."
        return False, "No match."


class ContextCapturingBackend:
    """Records what context_before was passed to classify."""

    def __init__(self) -> None:
        # Sentinel "UNSET" distinguishes "never called" from "called with None".
        self.last_context: str | None = "UNSET"

    def classify(
        self,
        text: str,
        prompt: str,
        model: str,
        context_before: str | None = None,
    ) -> tuple[bool, str]:
        self.last_context = context_before
        return True, "match"


def test_semantic_pass_with_mock() -> None:
    blocks = _make_blocks()
    # Profile with no regex patterns, only semantic
    profile = ExtractionProfile(
        name="semantic_only",
        description="semantic test",
        patterns=[],
        semantic_prompt="Is this caretaking?",
        context_window=1,
    )
    result = extract(_conv(blocks), profile, backend=FakeBackend(), skip_semantic=False)
    assert result.semantic_matches == 1
    assert result.matches[0].block.index == 1
    assert result.matches[0].tier == "semantic"


def test_multi_pattern_match_produces_single_entry() -> None:
    block = Block(
        block_type="response",
        timestamp="1:00",
        content="Go eat something. You've been working all day.",
        index=0,
    )
    profile = ExtractionProfile(
        name="multi",
        description="multi-pattern test",
        patterns=["go eat", "you've been working"],
        semantic_prompt="",
    )
    result = extract(_conv([block]), profile, skip_semantic=True)
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.reason.startswith("Patterns: ")
    assert "go eat" in match.reason
    assert "you've been working" in match.reason


def test_semantic_skips_regex_matches() -> None:
    blocks = _make_blocks()
    # Profile with regex that catches "go eat" + semantic that also looks at block 1
    profile = ExtractionProfile(
        name="dedup",
        description="dedup test",
        patterns=["go eat"],
        semantic_prompt="Is this caretaking?",
        context_window=1,
    )
    result = extract(_conv(blocks), profile, backend=FakeBackend(), skip_semantic=False)
    # Block 1 matched by regex already, semantic should not re-add it
    block1_matches = [m for m in result.matches if m.block.index == 1]
    assert len(block1_matches) == 1
    assert block1_matches[0].tier == "regex"


def test_target_prompt_skips_responses() -> None:
    """target=prompt only matches prompt blocks even if response would match."""
    blocks = [
        Block("prompt", "1:00", "I just wanted the simple version", 0),
        Block("response", "1:01", "I just wanted to add error handling", 1),
    ]
    profile = ExtractionProfile(
        name="t",
        description="t",
        patterns=["I just wanted"],
        target="prompt",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 1
    assert result.matches[0].block.block_type == "prompt"


def test_target_response_skips_prompts() -> None:
    blocks = [
        Block("prompt", "1:00", "go eat", 0),
        Block("response", "1:01", "go eat", 1),
    ]
    profile = ExtractionProfile(
        name="t",
        description="t",
        patterns=["go eat"],
        target="response",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 1
    assert result.matches[0].block.block_type == "response"


def test_target_both_matches_both() -> None:
    blocks = [
        Block("prompt", "1:00", "I just wanted clarity", 0),
        Block("response", "1:01", "I just wanted to acknowledge that", 1),
    ]
    profile = ExtractionProfile(
        name="t",
        description="t",
        patterns=["I just wanted"],
        target="both",
    )
    result = extract(_conv(blocks), profile, skip_semantic=True)
    assert len(result.matches) == 2
    assert {m.block.block_type for m in result.matches} == {"prompt", "response"}


def test_semantic_pass_receives_prior_block_content() -> None:
    blocks = [
        Block(
            "prompt",
            "1:00",
            "Make it shorter, please — the previous one was too verbose.",
            0,
        ),
        Block(
            "response",
            "1:01",
            "Here is the much longer expanded version with examples and edge cases.",
            1,
        ),
        Block(
            "prompt",
            "1:02",
            "Make it shorter again — same problem, way too long.",
            2,
        ),
    ]
    profile = ExtractionProfile(
        name="t",
        description="t",
        patterns=[],
        semantic_prompt="Is this recognition?",
        target="prompt",
    )
    backend = ContextCapturingBackend()
    extract(_conv(blocks), profile, backend=backend, skip_semantic=False)
    assert backend.last_context is not None
    assert "expanded version" in backend.last_context


def test_semantic_pass_first_block_has_no_context() -> None:
    blocks = [
        Block("prompt", "1:00", "wait what — that's not what I meant at all", 0),
    ]
    profile = ExtractionProfile(
        name="t",
        description="t",
        patterns=[],
        semantic_prompt="Is this recognition?",
        target="prompt",
    )
    backend = ContextCapturingBackend()
    extract(_conv(blocks), profile, backend=backend, skip_semantic=False)
    assert backend.last_context is None
