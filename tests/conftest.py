"""Shared fixtures.

The whole suite runs offline with no credentials: the model is the deterministic
:class:`~blindspot.llm.mock.MockProvider`, and everything else is real code.
That is deliberate -- a contributor can prove the orchestration, sandboxing,
schema repair and grading all work before spending a single token.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from blindspot.config import RunConfig
from blindspot.corpus import Case, load_task
from blindspot.types import CaseMeta

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = REPO_ROOT / "spectrap" / "tasks"


@pytest.fixture
def mock_config(tmp_path: Path) -> RunConfig:
    return RunConfig(
        provider="mock",
        model_family="mock",
        cassette_dir=tmp_path / "cassettes",
        results_dir=tmp_path / "results",
        trajectory_dir=tmp_path / "trajectories",
        concurrency=2,
        sandbox_timeout_s=30.0,
        repair_attempts=1,
        max_obligations=3,
    )


ADDER_SPEC = """# TICKET-1 — Add two integers

## What to build

```python
def add(a: int, b: int) -> int:
    ...
```

The function must return the sum of its two arguments.

If either argument is not an integer, it must raise `TypeError`.

An overflow is not possible in Python and does not need handling.
"""

ADDER_GOOD = """def add(a, b):
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("integers required")
    return a + b
"""

ADDER_BAD = """def add(a, b):
    if not isinstance(a, int) or not isinstance(b, int):
        raise TypeError("integers required")
    return a - b
"""


@pytest.fixture
def synthetic_case(tmp_path: Path) -> Case:
    """A tiny (spec, buggy impl, reference) triple that needs no corpus."""
    task_dir = tmp_path / "tasks" / "adder"
    task_dir.mkdir(parents=True)
    (task_dir / "SPEC.md").write_text(ADDER_SPEC, encoding="utf-8")
    (task_dir / "reference.py").write_text(ADDER_GOOD, encoding="utf-8")
    (task_dir / "generators.py").write_text(
        "import random\n\n\n"
        "def sample(rng):\n"
        "    return ((rng.randint(-50, 50), rng.randint(-50, 50)), {})\n\n\n"
        "SEEDS = [((1, 1), {}), ((0, 0), {}), ((-3, 7), {})]\n",
        encoding="utf-8",
    )
    (task_dir / "selftest.py").write_text(
        "import impl\n\n\ndef test_add():\n    assert impl.add(2, 2) == 4\n", encoding="utf-8"
    )
    (task_dir / "task.yaml").write_text(
        yaml.safe_dump(
            {
                "task_id": "adder",
                "title": "Add two integers",
                "entrypoint": "add",
                "difficulty": 1,
                "grounding": {"standard": "none", "url": "https://example.invalid/spec"},
                "trap_class": "arithmetic/sign",
                "trap": "subtracts instead of adding",
                "why_models_miss_it": "synthetic fixture",
                "open_questions": ["q1", "q2"],
            }
        ),
        encoding="utf-8",
    )

    case_dir = tmp_path / "cases" / "adder__v0"
    case_dir.mkdir(parents=True)
    (case_dir / "impl.py").write_text(ADDER_BAD, encoding="utf-8")
    (case_dir / "self_tests.py").write_text(
        "import impl\n\n\ndef test_zero():\n    assert impl.add(0, 0) == 0\n", encoding="utf-8"
    )
    meta = CaseMeta(
        case_id="adder__v0",
        task_id="adder",
        split="dev",
        has_defect=True,
        entrypoint="add",
        witness_input="add(1, 1)",
    )
    (case_dir / "meta.yaml").write_text(yaml.safe_dump(meta.model_dump()), encoding="utf-8")

    return Case(meta=meta, task=load_task(task_dir), directory=case_dir)


@pytest.fixture
def clean_case(synthetic_case: Case) -> Case:
    """The same task with a correct implementation, for false-alarm tests."""
    directory = synthetic_case.directory.parent / "adder__v1"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "impl.py").write_text(ADDER_GOOD, encoding="utf-8")
    (directory / "self_tests.py").write_text(
        "import impl\n\n\ndef test_zero():\n    assert impl.add(0, 0) == 0\n", encoding="utf-8"
    )
    meta = synthetic_case.meta.model_copy(
        update={"case_id": "adder__v1", "has_defect": False, "witness_input": ""}
    )
    (directory / "meta.yaml").write_text(yaml.safe_dump(meta.model_dump()), encoding="utf-8")
    return Case(meta=meta, task=synthetic_case.task, directory=directory)
