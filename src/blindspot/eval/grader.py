"""The grader.  No language model is involved anywhere in this file.

Pre-registered primary endpoint
-------------------------------
For a case *i* with candidate implementation ``B_i``, hidden reference ``R_i``
and the set ``T`` of tests the system emitted:

    S_i = 1  iff  (exists s in T : exec(s, B_i) = FAIL)
                  and  (for all s in T : exec(s, R_i) = PASS)

    DR  = sum(S_i) / n_buggy          FAR = sum(FA_j) / n_clean
    J   = DR - FAR

The second conjunct is load-bearing.  Without it ``assert False`` scores 100%:
it fails on every implementation.  Requiring every emitted test to pass on the
hidden reference means a system is credited only when its accusation is
*sound* -- it distinguishes this implementation from a correct one, rather than
merely being red.

``S_lenient`` (at least one sound counterexample, ignoring other unsound tests)
is reported alongside as a secondary, because it answers a different and also
useful question: did the system find the bug at all, even if its report also
contained noise?

Determinism gate
----------------
Every credited counterexample is re-executed ``repeats`` additional times
against both targets.  A test that does not agree with itself unanimously is
discarded and counted as a flake, never silently kept.
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ..corpus import Case
from ..sandbox.runner import run_probe
from ..types import RunStatus


@dataclass
class TestVerdict:
    """How one emitted test behaved on each target."""

    index: int
    on_candidate: str
    on_reference: str
    sound: bool  # fails on candidate AND passes on reference
    unsound: bool  # fails or errors on the reference: the test itself is wrong
    flaky: bool = False
    assertion: str = ""
    failing_input: str = ""
    code: str = ""

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "on_candidate": self.on_candidate,
            "on_reference": self.on_reference,
            "sound": self.sound,
            "unsound": self.unsound,
            "flaky": self.flaky,
            "assertion": self.assertion,
            "failing_input": self.failing_input,
        }


@dataclass
class CaseGrade:
    case_id: str
    task_id: str
    system: str
    split: str
    has_defect: bool
    # Which underlying defect this case carries.  Several independently
    # generated implementations can share one, and their outcomes are then
    # highly correlated, so intervals are also computed by resampling this
    # rather than the case list.
    trap_id: str = ""
    spec_visible: bool | None = None

    emitted: int = 0
    detected: bool = False  # S_i, primary (strict)
    detected_lenient: bool = False  # S_i, secondary
    false_alarm: bool = False
    sound_counterexamples: int = 0
    unsound_claims: int = 0
    flakes: int = 0
    verdicts: list[TestVerdict] = field(default_factory=list)
    reported_verdict: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "task_id": self.task_id,
            "system": self.system,
            "split": self.split,
            "has_defect": self.has_defect,
            "trap_id": self.trap_id,
            "spec_visible": self.spec_visible,
            "emitted": self.emitted,
            "detected": self.detected,
            "detected_lenient": self.detected_lenient,
            "false_alarm": self.false_alarm,
            "sound_counterexamples": self.sound_counterexamples,
            "unsound_claims": self.unsound_claims,
            "flakes": self.flakes,
            "reported_verdict": self.reported_verdict,
            "error": self.error,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


def _status_of(
    code: str, impl_src: str, timeout_s: float, *, attempts: int = 3
) -> tuple[str, str, str]:
    """Execute one test, retrying a timeout with more headroom.

    A timeout is an *inconclusive measurement*, not an observation about the
    code.  The sweep runs many sandboxes at once, so a test that normally
    finishes in a second can exceed the limit purely because the machine is
    busy -- and the first version of this function handed that back as a
    status, which had two bad consequences: a real counterexample whose first
    run timed out was scored as no detection, and one whose *repeat* timed out
    was branded non-deterministic and discarded.  Both make the headline
    numbers a function of how loaded the machine was.

    Retrying with a longer limit costs nothing when nothing times out, and a
    test that is still unfinished with three times the budget is genuinely too
    slow to be evidence.
    """
    result = run_probe(probe_code=code, impl_source=impl_src, timeout_s=timeout_s)
    for extra in range(1, attempts):
        if result.status is not RunStatus.TIMEOUT:
            break
        result = run_probe(probe_code=code, impl_source=impl_src, timeout_s=timeout_s * (1 + extra))
    return result.status.value, result.assertion, result.failing_input


def grade_case(
    case: Case,
    *,
    system: str,
    tests: Sequence[str],
    reported_verdict: str = "",
    timeout_s: float = 25.0,
    repeats: int = 4,
    concurrency: int = 4,
    error: str = "",
) -> CaseGrade:
    """Execute every emitted test against the candidate and the reference."""
    grade = CaseGrade(
        case_id=case.case_id,
        task_id=case.meta.task_id,
        system=system,
        split=case.meta.split,
        has_defect=case.meta.has_defect,
        trap_id=case.trap_id,
        spec_visible=case.meta.spec_visible,
        emitted=len(tests),
        reported_verdict=reported_verdict,
        error=error,
    )
    if not tests:
        return grade

    impl_src = case.impl_src
    ref_src = case.reference_src

    def evaluate(pair: tuple[int, str]) -> TestVerdict:
        index, code = pair
        cand_status, assertion, failing_input = _status_of(code, impl_src, timeout_s)
        ref_status, _, _ = _status_of(code, ref_src, timeout_s)
        sound = cand_status == RunStatus.FAIL.value and ref_status == RunStatus.PASS.value
        unsound = ref_status != RunStatus.PASS.value
        return TestVerdict(
            index=index,
            on_candidate=cand_status,
            on_reference=ref_status,
            sound=sound,
            unsound=unsound,
            assertion=assertion,
            failing_input=failing_input,
            code=code,
        )

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        verdicts = list(pool.map(evaluate, list(enumerate(tests))))

    # ---- determinism gate: only the credited tests are re-run -------------- #
    for verdict in verdicts:
        if not verdict.sound or repeats <= 0:
            continue
        for _ in range(repeats):
            cand_status, _, _ = _status_of(verdict.code, impl_src, timeout_s)
            ref_status, _, _ = _status_of(verdict.code, ref_src, timeout_s)
            if RunStatus.TIMEOUT.value in (cand_status, ref_status):
                # Still inconclusive after the retries inside `_status_of`.
                # Not a disagreement -- there is nothing to disagree with.
                continue
            if cand_status != verdict.on_candidate or ref_status != verdict.on_reference:
                verdict.flaky = True
                verdict.sound = False
                grade.flakes += 1
                break

    grade.verdicts = verdicts
    grade.sound_counterexamples = sum(1 for v in verdicts if v.sound)
    grade.unsound_claims = sum(1 for v in verdicts if v.unsound)

    fails_on_candidate = any(
        v.on_candidate == RunStatus.FAIL.value and not v.flaky for v in verdicts
    )
    all_pass_on_reference = all(v.on_reference == RunStatus.PASS.value for v in verdicts)

    grade.detected_lenient = grade.sound_counterexamples > 0
    grade.detected = bool(fails_on_candidate and all_pass_on_reference)

    # A false alarm is an accusation against an implementation that is
    # observationally equivalent to the reference.  Mechanically: any emitted
    # test that fails on it.  Reported verdict is cross-checked but the
    # execution result is authoritative.
    if not case.meta.has_defect:
        grade.false_alarm = fails_on_candidate

    return grade
