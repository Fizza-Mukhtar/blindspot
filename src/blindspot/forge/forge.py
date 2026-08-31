"""The SpecTrap forge: build the benchmark instead of hand-writing it.

Why a forge rather than hand-injected bugs
------------------------------------------
The obvious objection to any self-built defect benchmark is "you wrote the bugs
*and* the detector".  The forge removes the author from that loop:

1. A model is given ``SPEC.md`` and nothing else, and asked to implement the
   ticket the way it normally would.  It has no knowledge that a benchmark
   exists, that a reference implementation exists, or that anything will later
   try to falsify its code.
2. The **same** model is then shown its own implementation and asked to write
   the test suite that ships with it -- exactly the workflow that produces the
   failure this project is about.
3. Those self-written tests are executed.  A variant is admitted only if they
   are **green**, because a red suite is the easy case that CI already catches.
4. The implementation is differentially fuzzed against the hidden, hand-written
   reference.  A concrete disagreement is the buggy label; no disagreement
   within the published budget is the clean label.
5. An independent second oracle -- the task's ``selftest.py``, whose assertions
   are traceable to the cited standard -- is run against the implementation.
   Whenever the two oracles disagree the case is flagged rather than silently
   labelled.

The headline statistic of the benchmark falls out of step 3 and 4 together:
**how often is a model's own test suite green while its code is provably
wrong.**  That number does not exist in the literature and it is measured here
rather than asserted.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel

from ..config import CASES_DIR, RunConfig
from ..corpus import Task, draw_split, load_tasks
from ..llm.router import LLMRouter, set_inflight_limit
from ..prompts import load as load_prompt
from ..sandbox.runner import run_suite
from ..types import CaseMeta, RunStatus
from .fuzz import differential

# Diversity at temperature 0: each variant is asked for a different, natural
# engineering posture rather than resampled from the same prompt.  This keeps
# the forge reproducible while still exploring more than one implementation.
# Realistic framings a working engineer might be under.  Two constraints on
# every entry: none of them mentions or gestures at any task's trap, and none
# asks for anything unusual -- a style that produced weird code would produce a
# benchmark of weird code.
#
# The list is long on purpose.  Prompts are sent at temperature 0, so two
# variants sharing a style are two *identical* requests and the second is just
# the first replayed.  With four styles, `--variants 12` silently meant four.
VARIANT_STYLES = [
    "Implement it straightforwardly, the way you would on a normal working day.",
    "You are short on time before a release cut. Implement it directly and keep it compact.",
    "You care about readability. Implement it cleanly, with small helper functions.",
    "You are porting this from another service. Implement it defensively.",
    "Reach for the standard library wherever it already does the job.",
    "Work through the ticket top to bottom, implementing each paragraph in the order it appears.",
    "You prefer explicit branching to clever one-liners. Spell the logic out.",
    "Keep the public function short and push the detail into private helpers.",
    "You are pairing with a junior engineer and narrating; keep the structure obvious.",
    "Validate the arguments first, then handle the main path in one pass over the input.",
    "You have been asked to keep the whole module under about sixty lines.",
    "Write it table-driven where a table fits more naturally than a chain of conditionals.",
]


class _CodePayload(BaseModel):
    code: str


@dataclass
class VariantOutcome:
    task_id: str
    variant: int
    case_id: str = ""
    admitted: bool = False
    reason: str = ""
    self_tests_green: bool = False
    self_tests_reject_reference: bool = False
    fuzz_status: str = ""
    fuzz_checked: int = 0
    witness: str = ""
    witness_detail: str = ""
    selftest_on_impl: str = ""
    oracles_agree: bool = True
    impl_chars: int = 0
    tests_chars: int = 0


@dataclass
class ForgeReport:
    variants: list[VariantOutcome] = field(default_factory=list)
    tasks: int = 0

    # Headline statistics of the corpus construction itself.
    green_and_wrong: int = 0
    green_and_right: int = 0
    red_suites: int = 0
    tests_reject_reference: int = 0
    oracle_disagreements: int = 0

    def to_dict(self) -> dict:
        usable = self.green_and_wrong + self.green_and_right
        return {
            "tasks": self.tasks,
            "variants_generated": len(self.variants),
            "self_tests_green": usable,
            "self_tests_red": self.red_suites,
            "green_but_provably_wrong": self.green_and_wrong,
            "green_and_equivalent": self.green_and_right,
            "green_and_wrong_rate": round(self.green_and_wrong / usable, 4) if usable else None,
            "self_tests_that_reject_the_correct_reference": self.tests_reject_reference,
            "oracle_disagreements": self.oracle_disagreements,
            "variants": [asdict(v) for v in self.variants],
        }


def _strip_fences(code: str) -> str:
    match = re.match(r"^\s*```(?:python)?\s*\n(.*?)\n```\s*$", code, re.S)
    return match.group(1) if match else code


def _module_imports_cleanly(source: str, entrypoint: str) -> str:
    """Cheap gate before spending sandbox time: does it parse and define the entrypoint?"""
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return f"syntax error: {exc}"
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }
    if entrypoint not in names:
        return f"does not define {entrypoint!r} (defines: {sorted(names) or 'nothing'})"
    return ""


def _existing_admitted(
    task_id: str, out_dir: Path, spec_variant: str = "detailed"
) -> tuple[int, int]:
    """Count cases already on disk for a (task, ticket rendition), for idempotency.

    A second forge pass -- a different implementing model, or the other ticket
    rendition -- must not create a second buggy case for a condition that
    already has one, or the corpus would drift every time the command is re-run.
    The two renditions are counted separately because they are separate
    experimental conditions.
    """
    buggy = clean = 0
    if not out_dir.is_dir():
        return (0, 0)
    for directory in out_dir.iterdir():
        meta_path = directory / "meta.yaml"
        if not meta_path.is_file():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if meta.get("task_id") != task_id:
            continue
        if meta.get("spec_variant", "detailed") != spec_variant:
            continue
        if meta.get("has_defect"):
            buggy += 1
        else:
            clean += 1
    return (buggy, clean)


def forge_task(
    task: Task,
    router: LLMRouter,
    *,
    variants: int = 3,
    clean_target: int = 2,
    buggy_target: int = 1,
    fuzz_budget: int = 3000,
    split: str = "test",
    out_dir: Path = CASES_DIR,
    impl_role: str = "smart",
    variant_offset: int = 0,
    spec_variant: str = "detailed",
) -> list[VariantOutcome]:
    """Generate, screen and admit cases for one task."""
    outcomes: list[VariantOutcome] = []
    spec = task.spec_for(spec_variant)
    buggy_admitted, clean_admitted = _existing_admitted(task.task_id, out_dir, spec_variant)

    for step in range(variants):
        variant = variant_offset + step
        outcome = VariantOutcome(task_id=task.task_id, variant=variant)
        outcomes.append(outcome)

        if buggy_admitted >= buggy_target and clean_admitted >= clean_target:
            outcome.reason = "not attempted: both quotas for this task are already full"
            continue

        style = VARIANT_STYLES[variant % len(VARIANT_STYLES)]
        try:
            impl_payload = router.structured(
                nonce=variant,
                purpose="forge_impl",
                system=load_prompt("forge_impl"),
                user=f"{style}\n\n# Ticket\n\n{spec}",
                schema=_CodePayload,
                role=impl_role,
                max_tokens=6000,
            )
        except Exception as exc:
            # One variant failing is a variant, not a task.  Letting this
            # propagate aborted the whole task on its first attempt, which is
            # how `--variants 6` silently produced exactly one.
            outcome.reason = f"skipped: {type(exc).__name__}: {exc}"[:300]
            continue
        impl_src = _strip_fences(impl_payload.code)
        outcome.impl_chars = len(impl_src)

        problem = _module_imports_cleanly(impl_src, task.entrypoint)
        if problem:
            outcome.reason = f"rejected: {problem}"
            continue

        try:
            tests_payload = router.structured(
                nonce=variant,
                purpose="forge_tests",
                system=load_prompt("forge_tests"),
                user=(
                    f"# Ticket\n\n{spec}\n\n"
                    f"# Your implementation (`impl.py`)\n\n```python\n{impl_src}\n```"
                ),
                schema=_CodePayload,
                # A whole test suite in one reply is the longest completion the
                # forge asks for.  At 8000 the model was being cut off mid-file
                # and the reply contained no parsable JSON at all.
                max_tokens=12000,
                role=impl_role,
            )
        except Exception as exc:
            outcome.reason = f"skipped: {type(exc).__name__}: {exc}"[:300]
            continue
        tests_src = _strip_fences(tests_payload.code)
        outcome.tests_chars = len(tests_src)

        # --- 3. are the model's own tests green on the model's own code? ---- #
        own = run_suite(suite_code=tests_src, impl_source=impl_src, timeout_s=120)
        outcome.self_tests_green = own.status is RunStatus.PASS
        if not outcome.self_tests_green:
            outcome.reason = f"rejected: self-written tests are {own.status.value} on own code"
            continue

        # Diagnostic: do the model's tests reject the *correct* implementation?
        on_reference = run_suite(
            suite_code=tests_src, impl_source=task.reference_src, timeout_s=120
        )
        outcome.self_tests_reject_reference = on_reference.status is not RunStatus.PASS

        # --- 4. oracle one: differential fuzzing against the reference ------ #
        fuzz = differential(
            reference_src=task.reference_src,
            candidate_src=impl_src,
            generators_src=task.generators_src,
            entrypoint=task.entrypoint,
            budget=fuzz_budget,
        )
        outcome.fuzz_status = fuzz.status
        outcome.fuzz_checked = fuzz.checked
        if fuzz.status in {"error", "timeout", "missing_entrypoint"}:
            outcome.reason = f"rejected: fuzz {fuzz.status} {fuzz.detail[:200]}"
            continue

        # --- 5. oracle two: the standard-traceable selftest ------------------ #
        authoritative = run_suite(
            suite_code=task.selftest_src,
            impl_source=impl_src,
            timeout_s=120,
            suite_name="test_selftest.py",
        )
        outcome.selftest_on_impl = authoritative.status.value

        has_defect = fuzz.differs
        selftest_says_defect = authoritative.status is not RunStatus.PASS
        outcome.oracles_agree = has_defect == selftest_says_defect

        if fuzz.witness is not None:
            outcome.witness = fuzz.witness.call_repr(task.entrypoint)
            outcome.witness_detail = fuzz.witness.describe()

        # A clean label requires *both* oracles to find nothing. If the
        # authoritative selftest fails while fuzzing found nothing, the fuzz
        # budget simply missed it; the case is buggy and the disagreement is
        # recorded rather than hidden.
        if not has_defect and selftest_says_defect:
            has_defect = True
            outcome.witness = "(found by authoritative selftest, not by fuzzing)"
            outcome.witness_detail = authoritative.assertion[:300]

        if has_defect:
            if buggy_admitted >= buggy_target:
                outcome.reason = "not admitted: task already has its buggy case"
                continue
            buggy_admitted += 1
        else:
            if clean_admitted >= clean_target:
                outcome.reason = "not admitted: clean quota for this task is full"
                continue
            clean_admitted += 1

        prefix = "t" if spec_variant == "terse" else "v"
        case_id = f"{task.task_id}__{prefix}{variant}"
        outcome.case_id = case_id
        outcome.admitted = True
        _write_case(
            out_dir / case_id,
            CaseMeta(
                case_id=case_id,
                task_id=task.task_id,
                split=split,  # type: ignore[arg-type]
                has_defect=has_defect,
                difficulty=task.difficulty,
                trap=task.trap if has_defect else "",
                trap_class=task.trap_class if has_defect else "",
                grounding=task.grounding_url,
                witness_input=outcome.witness,
                spec_variant=spec_variant,  # type: ignore[arg-type]
                provenance="forged",
                forged_by=router.config.resolve(impl_role),  # type: ignore[arg-type]
                self_tests_green=True,
                # Step 6: does the disagreement with the reference actually
                # break a *stated* requirement?  The authoritative suite has
                # already been run above; recording its verdict here is what
                # separates "violates the specification" from "differs from the
                # reference where the specification is silent".
                spec_visible=(outcome.selftest_on_impl == "fail") if has_defect else None,
                entrypoint=task.entrypoint,
                notes=outcome.witness_detail,
            ),
            impl_src=impl_src,
            tests_src=tests_src,
        )

    return outcomes


def _write_case(directory: Path, meta: CaseMeta, *, impl_src: str, tests_src: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "impl.py").write_text(impl_src.rstrip() + "\n", encoding="utf-8")
    (directory / "self_tests.py").write_text(tests_src.rstrip() + "\n", encoding="utf-8")
    (directory / "meta.yaml").write_text(
        yaml.safe_dump(meta.model_dump(), sort_keys=True, allow_unicode=True), encoding="utf-8"
    )


def forge_all(
    config: RunConfig,
    *,
    router: LLMRouter,
    tasks: list[Task] | None = None,
    variants: int = 3,
    clean_target: int = 2,
    buggy_target: int = 1,
    out_dir: Path = CASES_DIR,
    split_map: dict[str, str] | None = None,
    impl_role: str = "smart",
    variant_offset: int = 0,
    spec_variant: str = "detailed",
) -> ForgeReport:
    tasks = tasks if tasks is not None else load_tasks()
    if spec_variant != "detailed":
        tasks = [t for t in tasks if t.has_variant(spec_variant)]
    split_map = split_map or draw_split([t.task_id for t in tasks])
    report = ForgeReport(tasks=len(tasks))

    # Tasks are independent, so they forge in parallel.  Variants *within* a
    # task stay sequential because the admission quota (one buggy case, N clean)
    # is order-dependent, and a deterministic corpus is worth more than the
    # extra parallelism.
    def one(task: Task) -> list[VariantOutcome]:
        # A transient provider failure on one task must not destroy a run that
        # may already have spent an hour of quota on the other thirteen.  The
        # failure is recorded as an outcome and the sweep continues; forging is
        # idempotent, so re-running picks up exactly where it stopped.
        try:
            return forge_task(
                task,
                router,
                variants=variants,
                clean_target=clean_target,
                buggy_target=buggy_target,
                split=split_map.get(task.task_id, "test"),
                out_dir=out_dir,
                impl_role=impl_role,
                variant_offset=variant_offset,
                spec_variant=spec_variant,
            )
        except Exception as exc:
            return [
                VariantOutcome(
                    task_id=task.task_id,
                    variant=variant_offset,
                    reason=f"aborted: {type(exc).__name__}: {exc}"[:400],
                )
            ]

    set_inflight_limit(config.max_inflight or config.concurrency)
    with ThreadPoolExecutor(max_workers=max(1, config.concurrency)) as pool:
        for outcomes in pool.map(one, tasks):
            report.variants.extend(outcomes)
    report.variants.sort(key=lambda v: (v.task_id, v.variant))

    for outcome in report.variants:
        if not outcome.self_tests_green:
            report.red_suites += 1
            continue
        if outcome.self_tests_reject_reference:
            report.tests_reject_reference += 1
        if not outcome.oracles_agree:
            report.oracle_disagreements += 1
        if outcome.fuzz_status == "witness" or outcome.selftest_on_impl not in ("pass", ""):
            report.green_and_wrong += 1
        elif outcome.fuzz_status == "equivalent":
            report.green_and_right += 1

    return report


def write_forge_report(report: ForgeReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
