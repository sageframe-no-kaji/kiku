"""Tests for extraction profile loading."""

import tempfile
from pathlib import Path

import pytest

from kiku.profile import ExtractionProfile


def _write_yaml(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_load_valid_profile() -> None:
    path = _write_yaml("""
name: test_profile
description: A test profile
patterns:
  - "go eat"
  - "go to bed"
semantic_prompt: "Is this caretaking?"
context_window: 2
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.name == "test_profile"
    assert profile.description == "A test profile"
    assert len(profile.patterns) == 2
    assert profile.semantic_prompt == "Is this caretaking?"
    assert profile.context_window == 2


def test_missing_name_raises() -> None:
    path = _write_yaml("""
description: no name here
patterns:
  - "test"
""")
    with pytest.raises(ValueError, match="name"):
        ExtractionProfile.from_yaml(path)


def test_no_patterns_or_prompt_raises() -> None:
    path = _write_yaml("""
name: empty_profile
description: nothing to match
""")
    with pytest.raises(ValueError, match="patterns.*semantic_prompt"):
        ExtractionProfile.from_yaml(path)


def test_patterns_only_valid() -> None:
    path = _write_yaml("""
name: regex_only
description: regex only profile
patterns:
  - "hello"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.patterns == ["hello"]
    assert profile.semantic_prompt == ""


def test_semantic_only_valid() -> None:
    path = _write_yaml("""
name: semantic_only
description: semantic only profile
semantic_prompt: "Does this show concern?"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.patterns == []
    assert profile.semantic_prompt == "Does this show concern?"


def test_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        ExtractionProfile.from_yaml("/nonexistent/profile.yaml")


def test_default_model() -> None:
    path = _write_yaml("""
name: defaults
description: test defaults
patterns:
  - "test"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.model == "claude-sonnet-4-6"


def test_custom_model() -> None:
    path = _write_yaml("""
name: custom
description: custom model
model: claude-opus-4-20250514
patterns:
  - "test"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert "opus" in profile.model


def test_target_default_is_both() -> None:
    path = _write_yaml("""
name: t
description: t
patterns:
  - "x"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.target == "both"


def test_target_explicit_prompt() -> None:
    path = _write_yaml("""
name: t
description: t
target: prompt
patterns:
  - "x"
""")
    profile = ExtractionProfile.from_yaml(path)
    assert profile.target == "prompt"


def test_target_invalid_value_raises() -> None:
    path = _write_yaml("""
name: t
description: t
target: middle
patterns:
  - "x"
""")
    with pytest.raises(ValueError, match="target"):
        ExtractionProfile.from_yaml(path)
