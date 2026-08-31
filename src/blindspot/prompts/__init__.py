"""Agent instructions, kept as files rather than string literals.

The submission is required to include "the instructions that shape each agent".
Keeping every system prompt in a reviewable Markdown file next to the code --
rather than buried in an f-string -- means a judge can read exactly what each
agent was told without reading any Python, and means a prompt change shows up
as a reviewable diff.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


@cache
def load(name: str) -> str:
    """Load a prompt by stem, e.g. ``load("cartographer")``."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"no prompt named {name!r} in {PROMPTS_DIR}")
    return path.read_text(encoding="utf-8").strip()


def render(name: str, **values: object) -> str:
    """Load a prompt and substitute ``{{placeholders}}``."""
    text = load(name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def available() -> list[str]:
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.md"))
