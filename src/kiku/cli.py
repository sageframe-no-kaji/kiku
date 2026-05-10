"""Kiku CLI — extract language behaviors from AI conversations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kiku.extractor import extract
from kiku.formatter import format_results
from kiku.parsers import PARSERS, Conversation
from kiku.profile import ExtractionProfile


def _dispatch(path: Path) -> Conversation:
    """Dispatch the input path to the first registered parser that can handle it."""
    for parser in PARSERS:
        if parser.can_parse(path):
            convs = list(parser.parse(path))
            if len(convs) != 1:
                raise ValueError(
                    f"Parser {type(parser).__name__} yielded {len(convs)} "
                    "conversations; AT-04 will lift this restriction"
                )
            return convs[0]
    registered = [type(p).__name__ for p in PARSERS]
    raise ValueError(f"No parser can handle {path}. Registered: {registered}")


def _load_dotenv() -> None:
    """Load .env file from the kiku project root if it exists."""
    import os

    # Walk up from this file to find .env
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    _load_dotenv()
    args = _parse_args(argv)

    conversation_path = Path(args.conversation)
    if not conversation_path.exists():
        print(f"Error: file not found: {conversation_path}", file=sys.stderr)
        sys.exit(1)

    # Load profile
    profile = ExtractionProfile.from_yaml(args.profile)
    print(f"Profile: {profile.name}", file=sys.stderr)
    print(f"  {profile.description}", file=sys.stderr)

    # Parse via dispatched parser
    try:
        conversation = _dispatch(conversation_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  Parsed {len(conversation.blocks)} blocks", file=sys.stderr)

    if not conversation.blocks:
        print("Error: no blocks found in conversation", file=sys.stderr)
        sys.exit(1)

    # Get backend for semantic pass
    backend = None
    skip_semantic = args.regex_only
    if not skip_semantic and profile.semantic_prompt:
        try:
            from kiku.backends import get_backend

            backend = get_backend()
        except RuntimeError as e:
            print(f"  Warning: {e}", file=sys.stderr)
            print("  Running regex-only mode", file=sys.stderr)
            skip_semantic = True

    # Extract
    result = extract(
        conversation, profile, backend=backend, skip_semantic=skip_semantic
    )

    print(
        f"  Found {len(result.matches)} matches "
        f"({result.regex_matches} regex, {result.semantic_matches} semantic)",
        file=sys.stderr,
    )

    # Format and output
    output = format_results(result)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding="utf-8")
        print(f"  Output: {output_path}", file=sys.stderr)
    else:
        print(output)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="kiku",
        description="Extract language behaviors from AI conversation exports.",
    )
    parser.add_argument(
        "conversation",
        help="Path to conversation export (Markdown)",
    )
    parser.add_argument(
        "--profile",
        "-p",
        required=True,
        help="Path to extraction profile (YAML)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--regex-only",
        action="store_true",
        help="Skip semantic pass, regex patterns only",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
