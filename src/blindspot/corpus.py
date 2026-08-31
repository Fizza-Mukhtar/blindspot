"""Loading the SpecTrap task library and the forged case set.

Layout
------
``spectrap/tasks/<task_id>/``   authored by hand, committed, never seen by any
                               system under evaluation except ``SPEC.md``
    SPEC.md          the ticket
    reference.py     the hidden correct implementation (grader only)
    generators.py    domain-aware input sampler for differential fuzzing
    selftest.py      authoritative assertions traceable to the cited standard
    task.yaml        metadata, grounding, declared open questions

``spectrap/cases/<case_id>/``   produced by ``blindspot forge``, committed
    impl.py          the model's implementation, written from SPEC.md alone
    self_tests.py    the tests that same model wrote for its own code
    meta.yaml        label, witness, provenance

A case never duplicates ``SPEC.md`` or ``reference.py``; it points at its task.
That keeps a single source of truth and makes drift impossible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import yaml

from .config import CASES_DIR, TASKS_DIR
from .types import CaseMeta, sha256_text


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    entrypoint: str
    difficulty: int
    grounding_url: str
    grounding_standard: str
    trap_class: str
    trap: str
    why_models_miss_it: str
    open_questions: list[str]
    directory: Path

    @cached_property
    def spec(self) -> str:
        return self.spec_for("detailed")

    def spec_for(self, variant: str) -> str:
        """The ticket, in one of two renditions.

        ``detailed`` is a thorough requirements document: every rule enumerated
        under its own heading.  ``terse`` states the *same* requirements the way
        a working engineer actually writes a ticket -- in prose, with the tricky
        clause present but not signposted, and normative points carried by
        reference to the cited standard.

        Both must fully determine the behaviour; ``docs/SPEC_FAIRNESS.md`` records
        the independent audit of that claim for every terse ticket.  Which
        rendition a case used is stored on the case, and the auditing system is
        always shown the *same* rendition the implementer saw.
        """
        name = "SPEC.terse.md" if variant == "terse" else "SPEC.md"
        path = self.directory / name
        if not path.is_file():
            path = self.directory / "SPEC.md"
        return path.read_text(encoding="utf-8")

    def has_variant(self, variant: str) -> bool:
        return (self.directory / ("SPEC.terse.md" if variant == "terse" else "SPEC.md")).is_file()

    @cached_property
    def reference_src(self) -> str:
        return (self.directory / "reference.py").read_text(encoding="utf-8")

    @cached_property
    def generators_src(self) -> str:
        return (self.directory / "generators.py").read_text(encoding="utf-8")

    @cached_property
    def selftest_src(self) -> str:
        return (self.directory / "selftest.py").read_text(encoding="utf-8")

    @property
    def spec_sha256(self) -> str:
        return sha256_text(self.spec)


def load_task(directory: Path) -> Task:
    meta = yaml.safe_load((directory / "task.yaml").read_text(encoding="utf-8"))
    grounding = meta.get("grounding") or {}
    return Task(
        task_id=meta["task_id"],
        title=meta.get("title", meta["task_id"]),
        entrypoint=meta["entrypoint"],
        difficulty=int(meta.get("difficulty", 3)),
        grounding_url=str(grounding.get("url", "")),
        grounding_standard=str(grounding.get("standard", "")),
        trap_class=str(meta.get("trap_class", "")),
        trap=str(meta.get("trap", "")).strip(),
        why_models_miss_it=str(meta.get("why_models_miss_it", "")).strip(),
        open_questions=list(meta.get("open_questions") or []),
        directory=directory,
    )


def load_tasks(root: Path = TASKS_DIR) -> list[Task]:
    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "task.yaml").is_file())
    return [load_task(d) for d in dirs]


def task_index(root: Path = TASKS_DIR) -> dict[str, Task]:
    return {t.task_id: t for t in load_tasks(root)}


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Case:
    meta: CaseMeta
    task: Task
    directory: Path

    @property
    def case_id(self) -> str:
        return self.meta.case_id

    @cached_property
    def impl_src(self) -> str:
        return (self.directory / "impl.py").read_text(encoding="utf-8")

    @cached_property
    def self_tests_src(self) -> str:
        path = self.directory / "self_tests.py"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    @property
    def spec(self) -> str:
        """The exact ticket rendition this case was forged from.

        The auditing system sees this, never the other rendition -- otherwise a
        detection would be measuring access to a better specification rather
        than the audit itself.
        """
        return self.task.spec_for(self.meta.spec_variant)

    @property
    def reference_src(self) -> str:
        return self.task.reference_src

    @property
    def entrypoint(self) -> str:
        return self.task.entrypoint

    @property
    def trap_id(self) -> str:
        """Identifies the *defect*, not the implementation that carries it.

        The forge generates many implementations per task, and several can fail
        on exactly the same witness -- the same misreading, written out twice.
        Grouping by (task, witness) is what lets the report say how many
        distinct bugs were actually found rather than how many files.
        """
        if not self.meta.has_defect:
            return ""
        return f"{self.meta.task_id}::{self.meta.witness_input or self.meta.notes}"


def load_case(directory: Path, tasks: dict[str, Task] | None = None) -> Case:
    meta = CaseMeta(**yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8")))
    tasks = tasks if tasks is not None else task_index()
    return Case(meta=meta, task=tasks[meta.task_id], directory=directory)


def load_cases(
    root: Path = CASES_DIR,
    *,
    split: str | None = None,
    only: list[str] | None = None,
    defective_only: bool = False,
    clean_only: bool = False,
) -> list[Case]:
    if not root.is_dir():
        return []
    tasks = task_index()
    cases: list[Case] = []
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (directory / "meta.yaml").is_file():
            continue
        case = load_case(directory, tasks)
        if split and case.meta.split != split:
            continue
        if only and case.case_id not in only:
            continue
        if defective_only and not case.meta.has_defect:
            continue
        if clean_only and case.meta.has_defect:
            continue
        cases.append(case)
    return cases


# --------------------------------------------------------------------------- #
# The dev/test split
# --------------------------------------------------------------------------- #

SPLIT_SEED = 20260828
DEV_SIZE = 4


def draw_split(
    task_ids: list[str], *, seed: int = SPLIT_SEED, dev_size: int = DEV_SIZE
) -> dict[str, str]:
    """Assign every task to ``dev`` or ``test`` with a published, seeded shuffle.

    Drawn once, before any system is run, and committed to
    ``spectrap/SPLIT.yaml``.  Prompt engineering and every design decision use
    the dev split only; the test split is the held-out measurement.
    """
    ordered = sorted(task_ids)
    rng = random.Random(seed)
    shuffled = ordered[:]
    rng.shuffle(shuffled)
    dev = set(shuffled[:dev_size])
    return {task_id: ("dev" if task_id in dev else "test") for task_id in ordered}
