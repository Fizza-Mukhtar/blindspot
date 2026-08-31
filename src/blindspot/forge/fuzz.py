"""Differential fuzzing between a candidate implementation and the reference.

This is the ground-truth oracle for the whole benchmark.  A SpecTrap case is
labelled *buggy* only when this module produces a concrete **witness**: an input
on which the candidate and the reference observably disagree.  A case is
labelled *clean* only when no witness exists within a fixed, published budget.

Neither label is ever assigned by a language model, and neither is assigned by
inspection.  That is the property the README leans on.

The whole search runs inside one sandboxed subprocess (``runner="script"``) so
that thousands of calls cost one process spawn rather than thousands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..sandbox.runner import RunStatus, SandboxSpec, run

# The driver executes inside the sandbox.  It imports the candidate and the
# reference side by side and compares observable outcomes: either a returned
# value or a raised exception type.  Comparison is by repr, which is stable,
# order-sensitive and immune to accidental __eq__ overrides in model-written
# code.
DRIVER = '''\
import json
import random
import sys
import traceback

import candidate
import generators
import reference

ENTRY = {entry!r}
BUDGET = {budget}
SEED = {seed}
MODE = {mode!r}

_ref_fn = getattr(reference, ENTRY)
_cand_fn = getattr(candidate, ENTRY, None)

EQUALS = getattr(generators, "equals", None)


def outcome(fn, args, kwargs):
    """Observable behaviour: a value, or the *type* of exception raised.

    Exception messages are deliberately excluded -- the specs require an
    exception type, not particular wording, so comparing messages would
    manufacture differences that are not defects.
    """
    try:
        value = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - classifying, not handling
        return ("raise", type(exc).__name__)
    return ("return", repr(value))


def same(a, b, args, kwargs):
    if a[0] != b[0]:
        return False
    if a[0] == "raise":
        return a[1] == b[1]
    if EQUALS is None:
        return a[1] == b[1]
    # A task may define a tolerant comparison (floats). Re-evaluate the values.
    try:
        return bool(EQUALS(_ref_fn(*args, **kwargs), _cand_fn(*args, **kwargs)))
    except Exception:
        return a[1] == b[1]


def emit(status, **extra):
    print("@@BLINDSPOT@@" + json.dumps({{"status": status, **extra}}))
    sys.exit(0)


if _cand_fn is None:
    emit("missing_entrypoint", entry=ENTRY)

inputs = []
for item in getattr(generators, "SEEDS", []):
    inputs.append(item)
rng = random.Random(SEED)
for _ in range(BUDGET):
    try:
        inputs.append(generators.sample(rng))
    except Exception:
        break

checked = 0
for args, kwargs in inputs:
    checked += 1
    try:
        ref = outcome(_ref_fn, args, kwargs)
    except Exception:
        continue  # generator produced something the reference cannot express
    try:
        cand = outcome(_cand_fn, args, kwargs)
    except Exception:
        cand = ("crash", traceback.format_exc(limit=1).strip().splitlines()[-1])
    if not same(ref, cand, args, kwargs):
        emit(
            "witness",
            checked=checked,
            args=repr(args),
            kwargs=repr(kwargs),
            reference=list(ref),
            candidate=list(cand),
        )

emit("equivalent", checked=checked)
'''


@dataclass
class Witness:
    """A concrete input on which candidate and reference disagree."""

    args_repr: str
    kwargs_repr: str
    reference_outcome: tuple[str, str]
    candidate_outcome: tuple[str, str]
    checked: int

    def call_repr(self, entrypoint: str) -> str:
        args = self.args_repr
        kwargs = self.kwargs_repr
        parts = []
        if args and args not in ("()", "(,)"):
            parts.append(args.strip("()").rstrip(","))
        if kwargs and kwargs != "{}":
            parts.append(f"**{kwargs}")
        return f"{entrypoint}({', '.join(p for p in parts if p.strip())})"

    def describe(self) -> str:
        def render(outcome: tuple[str, str]) -> str:
            kind, value = outcome
            if kind == "raise":
                return f"raises {value}"
            if kind == "crash":
                return f"crashes: {value}"
            return f"returns {value}"

        return (
            f"reference {render(self.reference_outcome)}; "
            f"candidate {render(self.candidate_outcome)}"
        )


@dataclass
class FuzzResult:
    status: str  # "witness" | "equivalent" | "missing_entrypoint" | "timeout" | "error"
    witness: Witness | None = None
    checked: int = 0
    detail: str = ""

    @property
    def differs(self) -> bool:
        return self.status == "witness"


def differential(
    *,
    reference_src: str,
    candidate_src: str,
    generators_src: str,
    entrypoint: str,
    budget: int = 3000,
    seed: int = 20260828,
    timeout_s: float = 120.0,
) -> FuzzResult:
    """Search for a witness separating ``candidate_src`` from ``reference_src``."""
    driver = DRIVER.format(entry=entrypoint, budget=budget, seed=seed, mode="differential")
    result = run(
        SandboxSpec(
            files={
                "reference.py": reference_src,
                "candidate.py": candidate_src,
                "generators.py": generators_src,
                "driver.py": driver,
            },
            entry="driver.py",
            runner="script",
            timeout_s=timeout_s,
            max_output_chars=400_000,
        )
    )
    if result.status is RunStatus.TIMEOUT:
        return FuzzResult(status="timeout", detail=f"exceeded {timeout_s}s")

    marker = "@@BLINDSPOT@@"
    line = next(
        (ln for ln in result.stdout.splitlines() if ln.startswith(marker)),
        None,
    )
    if line is None:
        return FuzzResult(
            status="error",
            detail=(result.stderr or result.stdout)[-1500:],
        )

    payload = json.loads(line[len(marker) :])
    status = payload["status"]
    if status == "witness":
        return FuzzResult(
            status=status,
            checked=int(payload.get("checked", 0)),
            witness=Witness(
                args_repr=payload["args"],
                kwargs_repr=payload["kwargs"],
                reference_outcome=tuple(payload["reference"]),  # type: ignore[arg-type]
                candidate_outcome=tuple(payload["candidate"]),  # type: ignore[arg-type]
                checked=int(payload.get("checked", 0)),
            ),
        )
    return FuzzResult(
        status=status,
        checked=int(payload.get("checked", 0)),
        detail=payload.get("entry", ""),
    )


def load_task_sources(task_dir: Path) -> dict[str, str]:
    return {
        "spec": (task_dir / "SPEC.md").read_text(encoding="utf-8"),
        "reference": (task_dir / "reference.py").read_text(encoding="utf-8"),
        "generators": (task_dir / "generators.py").read_text(encoding="utf-8"),
        "selftest": (task_dir / "selftest.py").read_text(encoding="utf-8"),
    }
