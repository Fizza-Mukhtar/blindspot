#!/usr/bin/env python
"""Remove build and run scratch, cross-platform.

Deliberately conservative: it never touches `cassettes/`, `spectrap/cases/`,
`results/expected/` or `trajectories/*.jsonl`, because those are the committed
evidence the reproduction path depends on.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBS = [
    "**/__pycache__",
    "**/*.pyc",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    "build",
    "*.egg-info",
    "src/*.egg-info",
]

removed = 0
for pattern in GLOBS:
    for path in ROOT.glob(pattern):
        if not path.exists():
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        removed += 1
print(
    f"removed {removed} scratch path(s); cassettes, cases, results/expected and "
    "trajectories were left untouched"
)
