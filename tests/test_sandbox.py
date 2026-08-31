"""The sandbox has to be right about four things, and it must be deterministic."""

from __future__ import annotations

from pathlib import Path

import pytest

from blindspot.sandbox.runner import normalise, run_probe
from blindspot.types import ProbeResult, RunStatus

IMPL = "def add(a, b):\n    return a + b\n"


def test_pass():
    result = run_probe(
        probe_code="import impl\n\n\ndef test_x():\n    assert impl.add(2, 2) == 4\n",
        impl_source=IMPL,
    )
    assert result.status is RunStatus.PASS


def test_fail_captures_the_headline_assertion():
    result = run_probe(
        probe_code="import impl\n\n\ndef test_x():\n    assert impl.add(2, 2) == 5\n",
        impl_source=IMPL,
    )
    assert result.status is RunStatus.FAIL
    assert "4" in result.assertion and "5" in result.assertion


def test_wrong_signature_is_an_error_not_a_failure():
    """A probe that cannot call the code is a broken probe, not evidence."""
    result = run_probe(
        probe_code="import impl\n\n\ndef test_x():\n    impl.add(1, 2, 3)\n", impl_source=IMPL
    )
    assert result.status is RunStatus.ERROR


def test_missing_module_is_an_error():
    result = run_probe(
        probe_code="import nope\n\n\ndef test_x():\n    assert True\n", impl_source=IMPL
    )
    assert result.status is RunStatus.ERROR


def test_timeout_is_bounded():
    result = run_probe(
        probe_code="import time\n\n\ndef test_x():\n    time.sleep(30)\n",
        impl_source=IMPL,
        timeout_s=5,
    )
    assert result.status is RunStatus.TIMEOUT


def test_network_is_blocked_and_not_reported_as_evidence():
    result = run_probe(
        probe_code=(
            "import socket\n\n\ndef test_x():\n"
            "    socket.create_connection(('example.invalid', 80))\n"
        ),
        impl_source=IMPL,
    )
    assert result.status is RunStatus.ERROR


def test_output_has_no_machine_specific_noise():
    """Memory addresses and temp paths would break byte-identical replay."""
    result = run_probe(
        probe_code="import impl\n\n\ndef test_x():\n    assert impl.add == 5\n", impl_source=IMPL
    )
    assert "0x" not in result.assertion or "0xADDR" in result.assertion
    assert "blindspot-sbx-" not in (result.stdout + result.stderr)


def test_normalise_scrubs_addresses_and_paths():
    text = "<function add at 0x00000229DD00B600> C:\\Temp\\blindspot-sbx-abc123\\test.py in 0.42s"
    scrubbed = normalise(text)
    assert "0x00000229DD00B600" not in scrubbed
    assert "blindspot-sbx-abc123" not in scrubbed


def test_repeated_runs_agree():
    code = "import impl\n\n\ndef test_x():\n    assert impl.add(2, 2) == 5\n"
    first = run_probe(probe_code=code, impl_source=IMPL)
    second = run_probe(probe_code=code, impl_source=IMPL)
    assert first.status == second.status
    assert first.assertion == second.assertion


@pytest.mark.slow
def test_hypothesis_is_available_and_derandomised():
    """Property probes must fail identically every time, or replay is a lie."""
    code = (
        "import impl\n"
        "from hypothesis import given, settings, strategies as st\n\n\n"
        "@settings(max_examples=50)\n"
        "@given(st.integers(min_value=0, max_value=100))\n"
        "def test_x(n):\n"
        "    assert impl.add(n, 1) < 50\n"
    )
    first = run_probe(probe_code=code, impl_source=IMPL)
    second = run_probe(probe_code=code, impl_source=IMPL)
    assert first.status is RunStatus.FAIL
    assert first.failing_input == second.failing_input


def test_a_locked_trajectory_file_does_not_kill_the_run(tmp_path, monkeypatch):
    """Observability must not be able to fail the thing it observes.

    Trajectories are written into the working tree, and a sync client or virus
    scanner can hold a handle open for a moment. Letting `PermissionError` out
    of the *logger* failed three otherwise-fine evaluation runs, which then
    looked like unexplained variance between two replays of the same cassettes.
    """
    from blindspot.trace.recorder import TrajectoryRecorder

    recorder = TrajectoryRecorder(tmp_path / "run.jsonl", run_id="r", case_id="c", system="s")

    calls = {"n": 0}
    real_open = Path.open

    def flaky_open(self, *args, **kwargs):
        if self.name == "run.jsonl":
            calls["n"] += 1
            raise PermissionError(13, "locked by another process")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky_open)
    recorder.note("this line cannot be written")  # must not raise
    monkeypatch.undo()

    assert calls["n"] >= 2, "the write should have been retried, not abandoned immediately"
    assert recorder.dropped == 1, "the loss should be counted, not hidden"

    recorder.note("this one lands")
    assert recorder.dropped == 1
    assert "this one lands" in (tmp_path / "run.jsonl").read_text(encoding="utf-8")


def test_a_slow_probe_is_retried_before_being_called_a_timeout(monkeypatch):
    """A busy machine must not change which path the pipeline takes.

    The adversary treats TIMEOUT as a broken probe and spends repair attempts on
    it. When a load-induced timeout appeared in one run and not another, two
    replays of the same cassettes diverged: one emitted a test the other did not.
    """
    from blindspot.sandbox import runner as runner_module

    seen: list[float] = []
    calls = {"n": 0}

    def fake_run(spec):
        seen.append(spec.timeout_s)
        calls["n"] += 1
        if calls["n"] == 1:
            return ProbeResult(status=RunStatus.TIMEOUT)
        return ProbeResult(status=RunStatus.FAIL, assertion="assert 1 == 2")

    monkeypatch.setattr(runner_module, "run", fake_run)
    result = runner_module.run_probe(probe_code="x", impl_source="y", timeout_s=10.0)

    assert result.status is RunStatus.FAIL
    assert seen == [10.0, 20.0], "the retry needs more headroom, not the same limit"


def test_a_genuinely_hanging_probe_still_times_out(monkeypatch):
    from blindspot.sandbox import runner as runner_module

    monkeypatch.setattr(runner_module, "run", lambda spec: ProbeResult(status=RunStatus.TIMEOUT))
    result = runner_module.run_probe(
        probe_code="x", impl_source="y", timeout_s=5.0, timeout_retries=3
    )
    assert result.status is RunStatus.TIMEOUT
