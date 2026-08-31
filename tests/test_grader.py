"""The grader is the load-bearing component: if it can be fooled, nothing else matters.

These tests encode the pre-registered scoring rule as executable specification.
"""

from __future__ import annotations

import pytest

from blindspot.agents.oracle import OraclePrediction, asserted_call, contradicts
from blindspot.agents.pipeline import _split_assertion
from blindspot.agents.referee import asserted_expectation
from blindspot.eval.grader import grade_case

SOUND = """import impl


def test_add_is_addition():
    assert impl.add(2, 3) == 5
"""

ASSERT_FALSE = """import impl


def test_always_red():
    assert impl is not None
    assert False
"""

WRONG_EXPECTATION = """import impl


def test_asserts_something_the_spec_never_said():
    assert impl.add(2, 3) == 6
"""

PASSES_EVERYWHERE = """import impl


def test_module_exists():
    assert hasattr(impl, "add")
"""

BROKEN_PROBE = """import impl


def test_wrong_signature():
    assert impl.add(1, 2, 3) == 3
"""


def test_sound_counterexample_is_credited(synthetic_case):
    grade = grade_case(synthetic_case, system="t", tests=[SOUND], repeats=1)
    assert grade.detected is True
    assert grade.detected_lenient is True
    assert grade.sound_counterexamples == 1
    assert grade.unsound_claims == 0


def test_assert_false_scores_zero(synthetic_case):
    """The whole point of the second conjunct.

    ``assert False`` fails on every implementation, including a correct one, so
    it is not evidence that *this* implementation is wrong.  A grader that only
    required "fails on the candidate" would score it 100%.
    """
    grade = grade_case(synthetic_case, system="t", tests=[ASSERT_FALSE], repeats=1)
    assert grade.detected is False
    assert grade.unsound_claims == 1


def test_a_wrong_expectation_is_not_a_detection(synthetic_case):
    """2 + 3 == 6 is red on both implementations, so it proves nothing."""
    grade = grade_case(synthetic_case, system="t", tests=[WRONG_EXPECTATION], repeats=1)
    assert grade.detected is False
    assert grade.unsound_claims == 1


def test_one_bad_test_poisons_the_report_under_the_strict_rule(synthetic_case):
    """Strict S_i requires *every* emitted test to pass on the reference.

    A report containing a real finding and a false accusation is not a
    trustworthy audit, so it does not score -- but the lenient secondary still
    records that the defect was found.
    """
    grade = grade_case(synthetic_case, system="t", tests=[SOUND, ASSERT_FALSE], repeats=1)
    assert grade.detected is False
    assert grade.detected_lenient is True
    assert grade.sound_counterexamples == 1
    assert grade.unsound_claims == 1


def test_passing_test_is_not_a_detection(synthetic_case):
    grade = grade_case(synthetic_case, system="t", tests=[PASSES_EVERYWHERE], repeats=1)
    assert grade.detected is False
    assert grade.unsound_claims == 0


def test_broken_probe_is_not_a_detection(synthetic_case):
    """A probe that cannot even call the function is not evidence."""
    grade = grade_case(synthetic_case, system="t", tests=[BROKEN_PROBE], repeats=1)
    assert grade.detected is False


def test_no_tests_means_no_detection_and_no_false_alarm(synthetic_case, clean_case):
    assert grade_case(synthetic_case, system="t", tests=[], repeats=1).detected is False
    assert grade_case(clean_case, system="t", tests=[], repeats=1).false_alarm is False


def test_false_alarm_on_a_clean_case(clean_case):
    """Accusing a correct implementation is a false alarm, whatever the report says."""
    grade = grade_case(clean_case, system="t", tests=[ASSERT_FALSE], repeats=1)
    assert grade.false_alarm is True
    assert grade.detected is False


def test_a_sound_test_does_not_fire_on_a_clean_case(clean_case):
    grade = grade_case(clean_case, system="t", tests=[SOUND], repeats=1)
    assert grade.false_alarm is False


@pytest.mark.slow
def test_determinism_gate_runs_repeats(synthetic_case):
    grade = grade_case(synthetic_case, system="t", tests=[SOUND], repeats=2)
    assert grade.detected is True
    assert grade.flakes == 0


# --------------------------------------------------------------------------- #
# What the referee is told the test claimed
#
# The referee is asked whether the spec requires the *asserted* result rather
# than the observed one.  When a probe fails by raising, the pytest output
# carries only the exception, so the claim has to be recovered from the probe
# itself -- mechanically, never by a model.
# --------------------------------------------------------------------------- #


def test_expectation_is_recovered_from_an_equality_assertion():
    code = "import impl\n\n\ndef test_x():\n    assert impl.f('bytes=500-500', 1) == [(0, 0)]\n"
    assert asserted_expectation(code) == "== [(0, 0)]"


def test_expectation_is_recovered_from_a_raises_block():
    code = (
        "import pytest\nimport impl\n\n\ndef test_x():\n"
        "    with pytest.raises(TypeError):\n        impl.f(1.5)\n"
    )
    assert asserted_expectation(code) == "raises TypeError"


def test_expectation_survives_an_unparseable_probe():
    assert asserted_expectation("def test_x(:  syntax error") == ""


def test_a_raised_exception_does_not_report_expected_equal_to_actual():
    """The reporting bug: both fields were filled from the observed exception,
    so a finding read 'expected X, produced X'."""
    code = "import impl\n\n\ndef test_x():\n    assert impl.f('bytes=500-500', 1) == [(0, 0)]\n"
    observed = "impl.UnsatisfiableRange: no requested range is satisfiable for this length"
    expected, actual = _split_assertion(observed, code)
    assert expected == "== [(0, 0)]"
    assert actual == observed
    assert expected != actual


def test_a_comparison_failure_still_splits_both_halves():
    expected, actual = _split_assertion("assert '1000.0 kB' == '1.0 MB'", "")
    assert expected == "'1.0 MB'"
    assert actual == "'1000.0 kB'"


# --------------------------------------------------------------------------- #
# The independent oracle
#
# The oracle predicts the answer without seeing the accusation; the comparison
# that follows is mechanical.  It may only ever WITHDRAW a finding.
# --------------------------------------------------------------------------- #


def test_oracle_withdraws_a_value_claim_when_the_spec_requires_an_exception():
    prediction = OraclePrediction(kind="raises", exception="UnsatisfiableRange")
    disagrees, why = contradicts(prediction, "== [(0, 0)]")
    assert disagrees
    assert "UnsatisfiableRange" in why


def test_oracle_withdraws_a_claim_whose_value_it_computes_differently():
    prediction = OraclePrediction(kind="value", value_repr="'1.0 MB'")
    assert contradicts(prediction, "== '1000.0 kB'")[0]


def test_oracle_leaves_an_agreeing_claim_alone():
    prediction = OraclePrediction(kind="value", value_repr="[(0, 0)]")
    assert not contradicts(prediction, "== [(0, 0)]")[0]


def test_oracle_abstention_never_withdraws():
    assert not contradicts(OraclePrediction(kind="unknown"), "== [(0, 0)]")[0]


def test_an_unparseable_claim_is_left_to_the_referee():
    prediction = OraclePrediction(kind="value", value_repr="[(0, 0)]")
    assert not contradicts(prediction, "== some_helper(x)")[0]
    assert not contradicts(prediction, "len(result) > 0")[0]


def test_oracle_agrees_that_an_exception_is_required():
    prediction = OraclePrediction(kind="raises", exception="TypeError")
    assert not contradicts(prediction, "raises TypeError")[0]
    assert contradicts(prediction, "raises ValueError")[0]


def test_the_call_under_test_is_extracted_without_the_module_prefix():
    code = (
        "import impl\n\n\ndef test_x():\n"
        "    assert impl.resolve_range('bytes=500-500', 1) == [(0, 0)]\n"
    )
    assert asserted_call(code, entrypoint="resolve_range") == "resolve_range('bytes=500-500', 1)"


def test_the_call_is_found_inside_a_raises_block_too():
    code = (
        "import pytest\nimport impl\n\n\ndef test_x():\n"
        "    with pytest.raises(TypeError):\n        impl.format_bytes(1.5)\n"
    )
    assert asserted_call(code) == "format_bytes(1.5)"


def test_the_call_is_found_when_the_probe_binds_the_result_first():
    """The shape that silently disabled the oracle on its first live run."""
    code = (
        "import impl\n\n\ndef test_range_clamping():\n"
        "    result = impl.resolve_range('bytes=500-500', 1)\n"
        "    assert result == [(0, 0)]\n"
    )
    assert asserted_call(code) == "resolve_range('bytes=500-500', 1)"
    assert asserted_call(code, entrypoint="resolve_range") == "resolve_range('bytes=500-500', 1)"


def test_no_call_to_the_module_under_test_yields_nothing():
    assert asserted_call("def test_x():\n    assert 1 == 1\n") == ""


def test_per_case_csv_header_matches_every_row(tmp_path):
    """The evidence file must line up.

    A column was added to the row writer while the header edit silently failed
    to apply, so every field after it shifted and `llm_calls` contained the
    string `CLEAN`. Every number in the README is recomputable from this file,
    so a one-column shift corrupts all of them at once.
    """
    import csv

    from blindspot.eval.grader import CaseGrade
    from blindspot.eval.report import write_per_case_csv
    from blindspot.eval.runner import RunRecord
    from blindspot.types import AuditReport, Verdict

    grade = CaseGrade(
        case_id="demo__v0",
        task_id="demo",
        system="blindspot",
        split="test",
        has_defect=True,
        trap_id="demo::f(1)",
        emitted=3,
        detected=True,
        unsound_claims=1,
        reported_verdict="DEFECT",
    )
    record = RunRecord(
        system="blindspot",
        case_id="demo__v0",
        report=AuditReport(case_id="demo__v0", system="blindspot", verdict=Verdict.DEFECT),
        grade=grade,
        trajectory="demo.jsonl",
    )

    path = tmp_path / "per_case.csv"
    write_per_case_csv([record], {}, path)

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header, body = rows[0], rows[1:]
    assert len(header) == len(set(header)), "duplicate column names"
    for row in body:
        assert len(row) == len(header), (
            f"row has {len(row)} fields but the header has {len(header)}"
        )

    # And the values must land in the columns they are named after.
    parsed = dict(zip(header, body[0], strict=True))
    assert parsed["case_id"] == "demo__v0"
    assert parsed["trap_id"] == "demo::f(1)"
    assert parsed["detected"] == "1"
    assert parsed["unsound_claims"] == "1"
    assert parsed["llm_calls"] == "0"
    assert parsed["reported_verdict"] == "DEFECT"


# --------------------------------------------------------------------------- #
# Timeouts are inconclusive, not decisive
# --------------------------------------------------------------------------- #


def test_a_timeout_is_retried_with_more_headroom(monkeypatch):
    """A busy machine must not be able to erase a counterexample.

    The sweep runs many sandboxes at once. Handing a load-induced timeout back
    as a status made a real counterexample score as no detection, and made a
    counterexample whose *repeat* timed out get branded non-deterministic.
    """
    from blindspot.eval import grader as grader_module
    from blindspot.types import ProbeResult, RunStatus

    seen: list[float] = []
    calls = {"n": 0}

    def fake_run_probe(*, probe_code, impl_source, timeout_s):
        seen.append(timeout_s)
        calls["n"] += 1
        if calls["n"] == 1:
            return ProbeResult(status=RunStatus.TIMEOUT)
        return ProbeResult(status=RunStatus.FAIL, assertion="assert 1 == 2")

    monkeypatch.setattr(grader_module, "run_probe", fake_run_probe)
    status, assertion, _ = grader_module._status_of("code", "impl", 10.0)

    assert status == RunStatus.FAIL.value, "the retry's verdict should win"
    assert assertion == "assert 1 == 2"
    assert seen == [10.0, 20.0], "the retry should get more headroom, not the same limit"


def test_a_test_that_always_times_out_stays_a_timeout(monkeypatch):
    from blindspot.eval import grader as grader_module
    from blindspot.types import ProbeResult, RunStatus

    monkeypatch.setattr(
        grader_module,
        "run_probe",
        lambda **_: ProbeResult(status=RunStatus.TIMEOUT),
    )
    status, _, _ = grader_module._status_of("code", "impl", 5.0, attempts=3)
    assert status == RunStatus.TIMEOUT.value
