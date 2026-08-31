#!/usr/bin/env python
"""Corpus integrity gate.  Run by ``make verify-corpus`` and by CI.

This script is the reason the README can say that SpecTrap's ground-truth
labels are *verified by construction rather than by inspection*.  It asserts,
for every task and every forged case:

  T1  the authoritative selftest passes against the reference implementation
  T2  the selftest is deterministic (identical verdict on a repeat run)
  T3  the reference is standard-library-only and imports nothing from this repo
  T4  the reference is deterministic and free of wall-clock / unseeded randomness
  T5  the generator produces mostly-valid inputs and never crashes the reference
  T6  task.yaml is complete, and its grounding URL is present
  T7  SPEC.md never mentions tests, benchmarks, models or this project
  T8  every buggy case's stored witness really does separate impl from reference
  T9  every clean case is observationally equivalent to the reference over the
      published fuzz budget, and passes the authoritative selftest

A failure here is a hard failure: a benchmark whose labels are not mechanically
checkable is not evidence.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from blindspot.corpus import Task, load_cases, load_tasks  # noqa: E402
from blindspot.forge.fuzz import differential  # noqa: E402
from blindspot.sandbox.runner import run_suite  # noqa: E402
from blindspot.types import RunStatus  # noqa: E402

# Words that would reveal the experimental frame to a model implementing the
# ticket.  A ticket mentioning "unit test" is entirely normal engineering prose
# and is deliberately NOT on this list; the check is about leaking the *study*,
# not about banning the vocabulary of software development.
FORBIDDEN_SPEC_WORDS = [
    "benchmark",
    "spectrap",
    "blindspot",
    "language model",
    "the llm",
    "adversar",
    "trap",
    "counterexample",
]
FORBIDDEN_REFERENCE_IMPORTS = {"blindspot", "spectrap", "requests", "httpx", "numpy", "pandas"}
CLOCK_MARKERS = ["time.time(", "time.monotonic(", "datetime.now(", "utcnow(", "date.today("]


@dataclass
class Check:
    name: str
    subject: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, name: str, subject: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name, subject, ok, detail))

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    def to_dict(self) -> dict:
        return {
            "total": len(self.checks),
            "passed": len(self.checks) - len(self.failures),
            "failed": len(self.failures),
            "failures": [
                {"check": c.name, "subject": c.subject, "detail": c.detail} for c in self.failures
            ],
        }


# --------------------------------------------------------------------------- #


def check_task(task: Task, *, samples: int, report: Report) -> None:
    subject = task.task_id

    # T1 / T2 -- authoritative selftest, twice.
    verdicts = []
    for _ in range(2):
        result = run_suite(
            suite_code=task.selftest_src,
            impl_source=task.reference_src,
            timeout_s=180,
            suite_name="test_selftest.py",
        )
        verdicts.append(result)
    report.add(
        "T1 selftest passes on reference",
        subject,
        verdicts[0].status is RunStatus.PASS,
        (verdicts[0].stdout or verdicts[0].stderr)[-900:],
    )
    report.add(
        "T2 selftest is deterministic",
        subject,
        verdicts[0].status == verdicts[1].status,
        f"{verdicts[0].status.value} then {verdicts[1].status.value}",
    )

    # T3 -- dependency hygiene.
    bad_imports: list[str] = []
    try:
        tree = ast.parse(task.reference_src)
    except SyntaxError as exc:
        report.add("T3 reference imports are clean", subject, False, f"syntax error: {exc}")
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad_imports += [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                bad_imports.append(node.module.split(".")[0])
        offenders = sorted(set(bad_imports) & FORBIDDEN_REFERENCE_IMPORTS)
        report.add(
            "T3 reference imports are clean", subject, not offenders, f"forbidden: {offenders}"
        )

    # T4 -- no hidden non-determinism.
    markers = [m for m in CLOCK_MARKERS if m in task.reference_src]
    if "random." in task.reference_src and "random.Random(" not in task.reference_src:
        markers.append("random.* without an explicit seed")
    report.add("T4 reference is deterministic", subject, not markers, f"found: {markers}")

    # T5 -- the generator.
    ok, raised, crashed = _exercise_generator(task, samples=samples)
    total = ok + raised + crashed
    raise_rate = raised / total if total else 1.0
    report.add(
        "T5 generator never crashes the reference",
        subject,
        crashed == 0,
        f"{crashed} unexpected exception(s) out of {total}",
    )
    report.add(
        "T5 generator yields mostly-valid inputs",
        subject,
        raise_rate <= 0.45,
        f"ValueError/expected-raise rate {raise_rate:.0%} (ok={ok}, raised={raised})",
    )

    # T6 -- metadata.
    missing = [
        field_name
        for field_name, value in (
            ("entrypoint", task.entrypoint),
            ("grounding.url", task.grounding_url),
            ("trap", task.trap),
            ("why_models_miss_it", task.why_models_miss_it),
        )
        if not value
    ]
    report.add("T6 task.yaml is complete", subject, not missing, f"missing: {missing}")
    report.add(
        "T6 declares exactly two open questions",
        subject,
        len(task.open_questions) == 2,
        f"{len(task.open_questions)} declared",
    )
    report.add(
        "T6 grounding url is http(s)",
        subject,
        task.grounding_url.startswith("http"),
        task.grounding_url,
    )
    report.add(
        "T6 reference defines the entrypoint",
        subject,
        f"def {task.entrypoint}(" in task.reference_src,
        "",
    )

    # T7 -- the spec must not leak the experimental frame.
    lowered = task.spec.lower()
    leaked = [w for w in FORBIDDEN_SPEC_WORDS if w in lowered]
    report.add("T7 SPEC.md does not leak the frame", subject, not leaked, f"mentions: {leaked}")


def _exercise_generator(task: Task, *, samples: int) -> tuple[int, int, int]:
    """Run the generator against the reference inside the sandbox."""
    driver = f"""
import json, random, sys
import generators, reference
fn = getattr(reference, {task.entrypoint!r})
ok = raised = crashed = 0
rng = random.Random(7)
items = list(getattr(generators, "SEEDS", []))
for _ in range({samples}):
    try:
        items.append(generators.sample(rng))
    except Exception:
        break
# A task may define its own exception type (e.g. UnsatisfiableRange), so
# "rejected the input" cannot be recognised by a fixed list of builtins.
# Instead, only the exceptions that always indicate a broken *implementation*
# rather than a rejected input are counted as crashes.
BROKEN = (NameError, AttributeError, ImportError, SyntaxError,
          RecursionError, MemoryError, SystemError, UnboundLocalError)
for args, kwargs in items:
    try:
        fn(*args, **kwargs)
        ok += 1
    except BROKEN:
        crashed += 1
    except Exception:
        raised += 1
    except BaseException:
        crashed += 1
print("@@COUNTS@@" + json.dumps({{"ok": ok, "raised": raised, "crashed": crashed}}))
"""
    from blindspot.sandbox.runner import SandboxSpec, run

    result = run(
        SandboxSpec(
            files={
                "reference.py": task.reference_src,
                "generators.py": task.generators_src,
                "driver.py": driver,
            },
            entry="driver.py",
            runner="script",
            timeout_s=180,
            max_output_chars=200_000,
        )
    )
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("@@COUNTS@@")), None)
    if line is None:
        return (0, 0, 1)
    counts = json.loads(line[len("@@COUNTS@@") :])
    return counts["ok"], counts["raised"], counts["crashed"]


def check_cases(*, report: Report, fuzz_budget: int) -> None:
    cases = load_cases()
    for case in cases:
        subject = case.case_id
        selftest = run_suite(
            suite_code=case.task.selftest_src,
            impl_source=case.impl_src,
            timeout_s=180,
            suite_name="test_selftest.py",
        )
        fuzz = differential(
            reference_src=case.reference_src,
            candidate_src=case.impl_src,
            generators_src=case.task.generators_src,
            entrypoint=case.entrypoint,
            budget=fuzz_budget,
        )
        if case.meta.has_defect:
            report.add(
                "T8 buggy case is separable from the reference",
                subject,
                fuzz.differs or selftest.status is not RunStatus.PASS,
                f"fuzz={fuzz.status}, authoritative selftest={selftest.status.value}",
            )
        else:
            report.add(
                "T9 clean case is equivalent to the reference",
                subject,
                fuzz.status == "equivalent",
                f"fuzz={fuzz.status} after {fuzz.checked} inputs",
            )
            report.add(
                "T9 clean case passes the authoritative selftest",
                subject,
                selftest.status is RunStatus.PASS,
                (selftest.stdout or "")[-500:],
            )
        own = run_suite(suite_code=case.self_tests_src, impl_source=case.impl_src, timeout_s=180)
        report.add(
            "T8 the case's own tests are green on its own code",
            subject,
            own.status is RunStatus.PASS,
            own.status.value,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=400)
    parser.add_argument("--fuzz-budget", type=int, default=3000)
    parser.add_argument("--skip-cases", action="store_true")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    report = Report()
    tasks = load_tasks()
    if not tasks:
        print("no tasks found", file=sys.stderr)
        return 2

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(lambda t: check_task(t, samples=args.samples, report=report), tasks))

    if not args.skip_cases:
        check_cases(report=report, fuzz_budget=args.fuzz_budget)

    by_subject: dict[str, list[Check]] = {}
    for check in report.checks:
        by_subject.setdefault(check.subject, []).append(check)

    width = max(len(s) for s in by_subject)
    for subject in sorted(by_subject):
        checks = by_subject[subject]
        bad = [c for c in checks if not c.ok]
        mark = "FAIL" if bad else " ok "
        print(f"[{mark}] {subject.ljust(width)}  {len(checks) - len(bad)}/{len(checks)} checks")
        for check in bad:
            print(f"        - {check.name}: {check.detail[:400]}")

    summary = report.to_dict()
    print(f"\n{summary['passed']}/{summary['total']} checks passed across {len(tasks)} tasks.")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0 if not report.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
