"""Tests for the Anthropic export parser."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from kiku.parsers import Conversation, Parser
from kiku.parsers.anthropic import AnthropicParser


@pytest.fixture
def synthetic_zip(tmp_path: Path) -> Path:
    """Build a tiny ZIP with conversations.json from the synthetic fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "anthropic_synthetic.json"
    data = fixture_path.read_text()
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", data)
    return zip_path


def test_parser_satisfies_protocol() -> None:
    assert isinstance(AnthropicParser(), Parser)


def test_can_parse_zip_with_conversations(synthetic_zip: Path) -> None:
    parser = AnthropicParser()
    assert parser.can_parse(synthetic_zip) is True


def test_can_parse_rejects_non_zip(tmp_path: Path) -> None:
    txt = tmp_path / "not.zip"
    txt.write_text("hello")
    assert AnthropicParser().can_parse(txt) is False


def test_can_parse_rejects_zip_without_conversations(tmp_path: Path) -> None:
    zip_path = tmp_path / "wrong.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("other.json", "{}")
    assert AnthropicParser().can_parse(zip_path) is False


def test_parse_yields_conversation(synthetic_zip: Path) -> None:
    convs = list(AnthropicParser().parse(synthetic_zip))
    assert len(convs) == 1
    conv = convs[0]
    assert isinstance(conv, Conversation)
    assert conv.id == "conv-001"
    assert conv.name == "Test Conversation"


def test_parse_produces_two_blocks(synthetic_zip: Path) -> None:
    conv = next(AnthropicParser().parse(synthetic_zip))
    assert len(conv.blocks) == 2
    prompt, response = conv.blocks
    assert prompt.block_type == "prompt"
    assert response.block_type == "response"


def test_block_content_excludes_thinking(synthetic_zip: Path) -> None:
    """The `text` field is pre-concatenated text-only; thinking blocks are excluded."""
    conv = next(AnthropicParser().parse(synthetic_zip))
    response = conv.blocks[1]
    assert "Let me think about this carefully" not in response.content
    assert "Here's a draft introduction." in response.content


def test_block_indices_sequential(synthetic_zip: Path) -> None:
    conv = next(AnthropicParser().parse(synthetic_zip))
    assert [b.index for b in conv.blocks] == [0, 1]


def test_unknown_sender_raises(tmp_path: Path) -> None:
    bad = [
        {
            "uuid": "c1",
            "name": "Bad",
            "created_at": "2026-04-14T09:00:00.000Z",
            "updated_at": "2026-04-14T09:00:00.000Z",
            "chat_messages": [
                {
                    "uuid": "m1",
                    "sender": "system",
                    "text": "hi",
                    "created_at": "2026-04-14T09:00:00.000Z",
                }
            ],
        }
    ]
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps(bad))
    with pytest.raises(ValueError, match="Unknown sender"):
        list(AnthropicParser().parse(zip_path))


def test_empty_chat_messages(tmp_path: Path) -> None:
    """Conversation with no messages parses without error to an empty block list."""
    empty = [
        {
            "uuid": "c1",
            "name": "Empty",
            "created_at": "2026-04-14T09:00:00.000Z",
            "updated_at": "2026-04-14T09:00:00.000Z",
            "chat_messages": [],
        }
    ]
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps(empty))
    convs = list(AnthropicParser().parse(zip_path))
    assert len(convs) == 1
    assert convs[0].blocks == []


def test_parse_yields_multiple_conversations(tmp_path: Path) -> None:
    multi = [
        {
            "uuid": "c1",
            "name": "First",
            "created_at": "2026-04-14T09:00:00.000Z",
            "updated_at": "2026-04-14T09:00:00.000Z",
            "chat_messages": [
                {
                    "uuid": "m1",
                    "sender": "human",
                    "text": "hi",
                    "created_at": "2026-04-14T09:00:00.000Z",
                }
            ],
        },
        {
            "uuid": "c2",
            "name": "Second",
            "created_at": "2026-04-14T09:00:00.000Z",
            "updated_at": "2026-04-14T09:00:00.000Z",
            "chat_messages": [
                {
                    "uuid": "m2",
                    "sender": "human",
                    "text": "hi",
                    "created_at": "2026-04-14T09:00:00.000Z",
                }
            ],
        },
    ]
    zip_path = tmp_path / "multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps(multi))
    convs = list(AnthropicParser().parse(zip_path))
    assert [c.id for c in convs] == ["c1", "c2"]
    assert [c.name for c in convs] == ["First", "Second"]
