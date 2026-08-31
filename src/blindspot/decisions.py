"""The human checkpoint.

Rule Book #04 and #05 require consequential actions to be gated behind human
approval and a qualified human reviewer to be part of any solution that could
significantly affect someone.  In an auditing tool the consequential act is
**accusing an engineer's code of being wrong**, and the place where that
judgement is least safe to automate is a genuine gap in the specification.

So the design rule is simple and absolute:

    An unresolved ambiguity is never reported as a defect.

Blindspot escalates instead.  ``blindspot decide`` walks a human through the
open questions for a task, one at a time, and writes their answers to
``decisions/<task_id>.yaml`` -- a committed, reviewable, replayable artefact.
Later runs apply those answers automatically, so a team answers each question
once rather than once per pull request.

Answers are keyed by a hash of the *normalised question text* rather than by
the model-assigned id, because ids are regenerated on every run while the
question a specification leaves open is stable.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .config import REPO_ROOT
from .types import sha256_text

DECISIONS_DIR = REPO_ROOT / "decisions"
_WS = re.compile(r"[^a-z0-9 ]+")


def question_key(question: str) -> str:
    """Stable key for a question, robust to punctuation and casing drift."""
    normalised = _WS.sub(" ", question.lower())
    normalised = " ".join(normalised.split())
    return sha256_text(normalised)[:16]


def decisions_path(task_id: str) -> Path:
    return DECISIONS_DIR / f"{task_id}.yaml"


def load_decisions(task_id: str) -> dict[str, str]:
    """Return ``{question_key: resolution}`` for a task, or an empty mapping."""
    path = decisions_path(task_id)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(entry["key"]): str(entry["resolution"])
        for entry in raw.get("decisions", [])
        if entry.get("resolution")
    }


def save_decision(
    task_id: str, *, question: str, resolution: str, options: list[str], decided_by: str
) -> Path:
    """Append or update one human decision."""
    path = decisions_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    raw = raw or {"task_id": task_id, "decisions": []}

    key = question_key(question)
    entry = {
        "key": key,
        "question": question,
        "options": options,
        "resolution": resolution,
        "decided_by": decided_by,
    }
    existing = [d for d in raw["decisions"] if d.get("key") != key]
    raw["decisions"] = sorted([*existing, entry], key=lambda d: d["key"])
    path.write_text(
        "# Human decisions on questions the specification does not settle.\n"
        "# Written by `blindspot decide`. Reviewed like any other source file.\n"
        + yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    return path
