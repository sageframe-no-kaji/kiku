"""Tests for conversation parser."""

from kiku.parsers import PARSERS, Parser
from kiku.parsers.claude_markdown import ClaudeMarkdownParser
from kiku.parsers.claude_markdown import _parse_blocks as parse_conversation

SAMPLE_CONVERSATION = """# Conversation Title

**Created:** 4/14/2026 7:07:26

## Prompt:
4/14/2026, 7:07:27 AM

Help me write something good.



## Response:
4/14/2026, 7:07:46 AM

````plaintext
Thought process: Thinking about the task.

Let me analyze this request carefully.
````

Here is a great draft for you.

## Prompt:
4/14/2026, 7:15:18 AM

Make it better.



## Response:
4/14/2026, 7:15:35 AM

Here is the improved version. Much better now.
"""


def test_parse_basic_conversation() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    assert len(blocks) == 4


def test_block_types() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    assert blocks[0].block_type == "prompt"
    assert blocks[1].block_type == "response"
    assert blocks[2].block_type == "prompt"
    assert blocks[3].block_type == "response"


def test_timestamps_extracted() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    assert blocks[0].timestamp == "4/14/2026, 7:07:27 AM"
    assert blocks[1].timestamp == "4/14/2026, 7:07:46 AM"


def test_thinking_blocks_stripped() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    response = blocks[1]
    assert "Thought process" not in response.content
    assert "Here is a great draft" in response.content


def test_content_preserved() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    assert "Help me write something good" in blocks[0].content
    assert "Make it better" in blocks[2].content
    assert "improved version" in blocks[3].content


def test_block_indices() -> None:
    blocks = parse_conversation(SAMPLE_CONVERSATION)
    assert blocks[0].index == 0
    assert blocks[1].index == 1
    assert blocks[2].index == 2
    assert blocks[3].index == 3


def test_empty_input() -> None:
    blocks = parse_conversation("")
    assert blocks == []


def test_no_headers() -> None:
    blocks = parse_conversation("Just some text with no headers.")
    assert blocks == []


def test_thinking_block_multi_paragraph_stripped() -> None:
    """Multi-paragraph thinking block is stripped; response content survives."""
    text = """## Response:
4/14/2026, 7:07:46 AM

````plaintext
Thought process: Initial analysis here.

Second paragraph of thinking.

Third paragraph.
````

Here is the actual response content."""
    blocks = parse_conversation(text)
    assert len(blocks) == 1
    assert "Thought process" not in blocks[0].content
    assert "Second paragraph" not in blocks[0].content
    assert "Here is the actual response content" in blocks[0].content


def test_thinking_block_header_only_line_stripped() -> None:
    """Thought process: on its own first line, with internal blanks, is stripped."""
    text = """## Response:
4/14/2026, 7:07:46 AM

````plaintext
Thought process:
First line of thinking after a newline start.

Second paragraph after a blank line.
````

Here is the actual response content."""
    blocks = parse_conversation(text)
    assert len(blocks) == 1
    assert "Thought process" not in blocks[0].content
    assert "First line of thinking" not in blocks[0].content
    assert "Here is the actual response content" in blocks[0].content


def test_claude_markdown_parser_satisfies_protocol() -> None:
    parser = ClaudeMarkdownParser()
    assert isinstance(parser, Parser)


def test_parsers_registry_shape() -> None:
    assert len(PARSERS) == 1
    assert all(isinstance(p, Parser) for p in PARSERS)
    assert isinstance(PARSERS[0], ClaudeMarkdownParser)
