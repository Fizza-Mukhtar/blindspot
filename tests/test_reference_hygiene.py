"""A guard against the bug class the corpus audit actually found.

The independent crosscheck (`make crosscheck`) found the *same* defect in four
reference implementations, written by four different authors working
independently on four unrelated tasks:

    re.compile(r"^...$")     accepts a trailing newline, because Python's `$`
                             also matches immediately before one
    \\d                       matches every Unicode decimal digit, and `int()`
                             accepts them, so non-ASCII numerals slip through

One of those four authors had *explicitly reasoned* about `int()` accepting
non-ASCII digits and chosen `[0-9]` for that reason — and still wrote `$`. The
correlated blind spot the whole project is about turned out to be present in the
project's own ground truth.

So the lesson gets encoded as an executable rule rather than a paragraph. This
test fails the build if any reference regresses, and it is the concrete answer
to "what would you do differently next time".

See CHANGELOG.md, iteration 4.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS = sorted(
    p for p in (REPO_ROOT / "spectrap" / "tasks").iterdir() if (p / "reference.py").is_file()
)

# A `$` that is not escaped and not inside a character class.
_DOLLAR_ANCHOR = re.compile(r"(?<!\\)\$")
_UNICODE_DIGIT = re.compile(r"(?<!\\)\\d")


def _regex_literals(source: str) -> list[tuple[int, str]]:
    """Every string literal passed to ``re.compile`` / ``re.match`` / ``re.fullmatch``."""
    tree = ast.parse(source)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", "")
        if name not in {"compile", "match", "fullmatch", "search", "sub", "split", "findall"}:
            continue
        for arg in node.args[:1]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.append((arg.lineno, arg.value))
    return found


@pytest.mark.parametrize("task_dir", TASKS, ids=lambda p: p.name)
def test_reference_regexes_anchor_with_Z_not_dollar(task_dir: Path):
    source = (task_dir / "reference.py").read_text(encoding="utf-8")
    offenders = [
        (line, pattern)
        for line, pattern in _regex_literals(source)
        if _DOLLAR_ANCHOR.search(pattern)
    ]
    assert not offenders, (
        f"{task_dir.name}/reference.py uses `$` in a regex: {offenders}. "
        "Python's `$` matches before a single trailing newline, so a value read "
        r"from a line-oriented source validates when it should not. Use `\Z`."
    )


@pytest.mark.parametrize("task_dir", TASKS, ids=lambda p: p.name)
def test_reference_regexes_use_ascii_digit_classes(task_dir: Path):
    source = (task_dir / "reference.py").read_text(encoding="utf-8")
    offenders = [
        (line, pattern)
        for line, pattern in _regex_literals(source)
        if _UNICODE_DIGIT.search(pattern)
    ]
    assert not offenders, (
        rf"{task_dir.name}/reference.py uses `\d` in a regex: {offenders}. "
        r"Python's `\d` matches every Unicode decimal digit and `int()` accepts "
        "them, so non-ASCII numerals pass validation. Use `[0-9]`."
    )


@pytest.mark.parametrize("task_dir", TASKS, ids=lambda p: p.name)
def test_references_are_stdlib_only_and_clock_free(task_dir: Path):
    """A reference that reads the clock or the network cannot be a stable oracle."""
    source = (task_dir / "reference.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    banned = {"blindspot", "spectrap", "requests", "httpx", "urllib", "socket", "os", "sys"}
    assert not (imported & banned), f"{task_dir.name} imports {sorted(imported & banned)}"

    for marker in ("time.time(", "time.monotonic(", "datetime.now(", "utcnow(", "date.today("):
        assert marker not in source, f"{task_dir.name}/reference.py calls {marker}"
