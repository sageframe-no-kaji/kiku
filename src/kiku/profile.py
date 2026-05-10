"""Load and validate extraction profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# PyYAML ships no type stubs; types-PyYAML is not in this project's deps
import yaml  # type: ignore[import-untyped]

ProfileTarget = Literal["prompt", "response", "both"]


@dataclass
class ExtractionProfile:
    """A profile describing a class of language behavior to extract."""

    name: str
    description: str
    patterns: list[str] = field(default_factory=list)
    semantic_prompt: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: int = 1
    target: ProfileTarget = "both"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExtractionProfile":
        """Load a profile from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a YAML mapping, got {type(data)}")

        name = data.get("name")
        if not name:
            raise ValueError("Profile must have a 'name' field")

        description = data.get("description", "")
        patterns = data.get("patterns", [])
        semantic_prompt = data.get("semantic_prompt", "")
        model = data.get("model", "claude-sonnet-4-6")
        context_window = data.get("context_window", 1)
        target = data.get("target", "both")

        if not patterns and not semantic_prompt:
            raise ValueError(
                "Profile must have at least 'patterns' or 'semantic_prompt'"
            )

        if not isinstance(patterns, list):
            raise ValueError("'patterns' must be a list of strings")

        if target not in ("prompt", "response", "both"):
            raise ValueError(
                f"Profile 'target' must be 'prompt', 'response', or 'both'; "
                f"got {target!r}"
            )

        return cls(
            name=name,
            description=description,
            patterns=[str(p) for p in patterns],
            semantic_prompt=str(semantic_prompt) if semantic_prompt else "",
            model=str(model),
            context_window=int(context_window),
            target=target,
        )
