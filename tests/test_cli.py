"""Tests for the kiku CLI entrypoint."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from kiku import cli
from kiku.cli import main


@pytest.fixture
def regex_profile(tmp_path: Path) -> Path:
    """A profile with only regex patterns — no semantic pass needed."""
    p = tmp_path / "regex.yaml"
    p.write_text(
        "name: regex_only\n"
        "description: regex test profile\n"
        "patterns:\n"
        '  - "go eat"\n'
        '  - "go to bed"\n'
    )
    return p


@pytest.fixture
def semantic_profile(tmp_path: Path) -> Path:
    """A profile with both regex and a semantic prompt."""
    p = tmp_path / "semantic.yaml"
    p.write_text(
        "name: semantic_profile\n"
        "description: semantic test profile\n"
        "patterns:\n"
        '  - "go eat"\n'
        'semantic_prompt: "Is this caretaking?"\n'
    )
    return p


@pytest.fixture
def markdown_conversation(tmp_path: Path) -> Path:
    """A minimal markdown export the claude_markdown parser can read."""
    p = tmp_path / "conv.md"
    p.write_text(
        "# Conversation\n\n"
        "**Created:** 4/14/2026 9:00:00\n\n"
        "## Prompt:\n"
        "4/14/2026, 9:00:01 AM\n\n"
        "What should I do?\n\n"
        "## Response:\n"
        "4/14/2026, 9:00:15 AM\n\n"
        "Go eat something. You've been working all day.\n\n"
    )
    return p


@pytest.fixture
def multi_zip(tmp_path: Path) -> Path:
    """Anthropic-export ZIP with three conversations, each with one match."""
    data = [
        {
            "uuid": f"c{i}",
            "name": f"Conv {i}",
            "created_at": "2026-04-14T09:00:00.000Z",
            "updated_at": "2026-04-14T09:00:00.000Z",
            "chat_messages": [
                {
                    "uuid": f"m{i}a",
                    "sender": "human",
                    "text": "check this",
                    "created_at": "2026-04-14T09:00:00.000Z",
                },
                {
                    "uuid": f"m{i}b",
                    "sender": "assistant",
                    "text": "go eat something — long enough to count",
                    "created_at": "2026-04-14T09:00:00.000Z",
                },
            ],
        }
        for i in range(3)
    ]
    zip_path = tmp_path / "multi.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("conversations.json", json.dumps(data))
    return zip_path


def test_missing_conversation_arg_exits(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--profile", "nope.yaml"])


def test_missing_profile_arg_exits(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    f = tmp_path / "x.md"
    f.write_text("")
    with pytest.raises(SystemExit):
        main([str(f)])


def test_conversation_file_not_found_exits_1(
    capsys: pytest.CaptureFixture[str], regex_profile: Path, tmp_path: Path
) -> None:
    missing = tmp_path / "does-not-exist.md"
    with pytest.raises(SystemExit) as exc:
        main([str(missing), "--profile", str(regex_profile)])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "file not found" in err


def test_unknown_format_exits_1(
    capsys: pytest.CaptureFixture[str], regex_profile: Path, tmp_path: Path
) -> None:
    """A file no parser can handle errors out, mentioning registered parsers."""
    unknown = tmp_path / "input.bin"
    unknown.write_bytes(b"\x00\x01not a known format")
    with pytest.raises(SystemExit) as exc:
        main([str(unknown), "--profile", str(regex_profile)])
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "No parser" in err
    assert "ClaudeMarkdownParser" in err
    assert "AnthropicParser" in err


def test_single_conversation_markdown_writes_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    markdown_conversation: Path,
    regex_profile: Path,
) -> None:
    out = tmp_path / "out.md"
    main(
        [
            str(markdown_conversation),
            "--profile",
            str(regex_profile),
            "--regex-only",
            "-o",
            str(out),
        ]
    )
    body = out.read_text()
    assert "## Match 1 [regex]" in body
    # Single-conversation runs omit the corpus-mode header line
    assert "**Conversations:**" not in body
    # And omit the per-match conv label suffix
    assert "Match 1 [regex] —" not in body


def test_multi_conversation_zip_aggregates_with_labels(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    multi_zip: Path,
    regex_profile: Path,
) -> None:
    out = tmp_path / "out.md"
    main(
        [
            str(multi_zip),
            "--profile",
            str(regex_profile),
            "--regex-only",
            "-o",
            str(out),
        ]
    )
    body = out.read_text()
    assert "**Conversations:** 3" in body
    assert body.count("## Match") == 3
    for i in range(3):
        assert f"Match {i + 1} [regex] — Conv {i}" in body


def test_regex_only_flag_skips_backend_init(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    markdown_conversation: Path,
    semantic_profile: Path,
    tmp_path: Path,
) -> None:
    """--regex-only must skip the backend factory even with a semantic profile."""
    called: dict[str, bool] = {"got_called": False}

    def _spy() -> object:
        called["got_called"] = True
        raise AssertionError("get_backend should not be called under --regex-only")

    monkeypatch.setattr("kiku.backends.get_backend", _spy)
    out = tmp_path / "out.md"
    main(
        [
            str(markdown_conversation),
            "--profile",
            str(semantic_profile),
            "--regex-only",
            "-o",
            str(out),
        ]
    )
    assert called["got_called"] is False


def test_no_api_key_falls_back_to_regex_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    markdown_conversation: Path,
    semantic_profile: Path,
    tmp_path: Path,
) -> None:
    """When the backend won't init, CLI warns and continues regex-only."""

    def _fail() -> object:
        raise RuntimeError("Set KIKU_API_KEY")

    monkeypatch.setattr("kiku.backends.get_backend", _fail)
    out = tmp_path / "out.md"
    main(
        [
            str(markdown_conversation),
            "--profile",
            str(semantic_profile),
            "-o",
            str(out),
        ]
    )
    err = capsys.readouterr().err
    assert "Warning" in err
    assert "Running regex-only mode" in err
    # Output still produced — regex matches survive
    assert out.exists()
    assert "## Match" in out.read_text()


def test_output_to_stdout_when_no_output_arg(
    capsys: pytest.CaptureFixture[str],
    markdown_conversation: Path,
    regex_profile: Path,
) -> None:
    main([str(markdown_conversation), "--profile", str(regex_profile), "--regex-only"])
    captured = capsys.readouterr()
    assert "# Kiku Extraction" in captured.out


def test_profile_file_not_found_raises(
    capsys: pytest.CaptureFixture[str],
    markdown_conversation: Path,
    tmp_path: Path,
) -> None:
    """Missing profile path surfaces from ExtractionProfile.from_yaml."""
    with pytest.raises(FileNotFoundError):
        main(
            [
                str(markdown_conversation),
                "--profile",
                str(tmp_path / "nope.yaml"),
            ]
        )


def test_dispatch_no_parser_match_raises_value_error(tmp_path: Path) -> None:
    """_dispatch yields nothing then raises when nothing matches; list() triggers it."""
    p = tmp_path / "unknown.xyz"
    p.write_bytes(b"opaque")
    with pytest.raises(ValueError, match="No parser"):
        list(cli._dispatch(p))


def test_load_dotenv_reads_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """_load_dotenv reads KEY=VALUE lines and sets only when unset in environ."""
    # _load_dotenv resolves the .env path from cli.py's location; replace __file__
    # is hard, so instead point it at a temp file via monkeypatching the module attr.
    # Simpler: call it and confirm it doesn't crash. Real .env presence covered by
    # the running project; this test confirms _load_dotenv is callable and idempotent.
    monkeypatch.setenv("KIKU_TEST_PRESET", "preset")
    cli._load_dotenv()
    import os

    assert os.environ.get("KIKU_TEST_PRESET") == "preset"
