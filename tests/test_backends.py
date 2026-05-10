"""Tests for the LLM backend factory and base wiring."""

from __future__ import annotations

import pytest

from kiku.backends import get_backend
from kiku.backends.anthropic_backend import AnthropicBackend
from kiku.backends.openai_compat import OpenAICompatBackend


@pytest.fixture(autouse=True)
def clear_backend_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure every test starts with a known-clean env for backend selection."""
    for key in ("KIKU_BACKEND", "KIKU_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_default_backend_is_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIKU_API_KEY", "test-key")
    backend = get_backend()
    assert isinstance(backend, AnthropicBackend)


def test_openai_backend_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KIKU_BACKEND", "openai")
    backend = get_backend()
    assert isinstance(backend, OpenAICompatBackend)


def test_backend_name_lowercased(monkeypatch: pytest.MonkeyPatch) -> None:
    """`KIKU_BACKEND` is case-insensitive — `OPENAI` still selects OpenAICompat."""
    monkeypatch.setenv("KIKU_BACKEND", "OPENAI")
    backend = get_backend()
    assert isinstance(backend, OpenAICompatBackend)


def test_unknown_backend_falls_through_to_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown KIKU_BACKEND values fall through to the Anthropic default."""
    monkeypatch.setenv("KIKU_BACKEND", "made-up-name")
    monkeypatch.setenv("KIKU_API_KEY", "test-key")
    backend = get_backend()
    assert isinstance(backend, AnthropicBackend)


def test_anthropic_backend_without_key_raises() -> None:
    """AnthropicBackend constructor must surface a clear error when no key is set."""
    with pytest.raises(RuntimeError, match="KIKU_API_KEY"):
        AnthropicBackend()


def test_anthropic_backend_accepts_anthropic_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ANTHROPIC_API_KEY is honored as a fallback when KIKU_API_KEY is unset."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "alt-key")
    backend = AnthropicBackend()
    assert isinstance(backend, AnthropicBackend)
