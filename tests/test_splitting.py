"""Regression tests for splitting a suite into one module per test.

A textual split severs `@pytest.mark.parametrize` from its function, which
turns the parameter into a missing fixture and reports the test as *errored*.
On the first real case that produced four bogus "unsound" verdicts. These
tests pin the AST-based behaviour that replaced it.
"""

from __future__ import annotations

from blindspot.eval.runner import _split_self_tests
from blindspot.sandbox.runner import run_probe
from blindspot.types import RunStatus

SUITE = """\
import pytest

import impl

CASES = [("1.0.0", True), ("bad", False)]


def helper(x):
    return x * 2


@pytest.fixture
def two():
    return 2


def test_plain():
    assert impl.add(1, 1) == 2


@pytest.mark.parametrize("tag,ok", CASES)
def test_parametrized(tag, ok):
    assert isinstance(tag, str) is True
    assert ok in (True, False)


def test_uses_fixture(two):
    assert impl.add(two, 0) == 2


def test_uses_helper():
    assert helper(2) == 4
"""

IMPL = "def add(a, b):\n    return a + b\n"


def test_produces_one_module_per_test():
    assert len(_split_self_tests(SUITE)) == 4


def test_every_produced_module_actually_runs():
    """The point of the fix: none of these may come back as ERROR."""
    for module in _split_self_tests(SUITE):
        result = run_probe(probe_code=module, impl_source=IMPL, timeout_s=40)
        assert result.status is RunStatus.PASS, f"{result.status}: {result.stdout[-400:]}"


def test_decorators_are_carried_with_their_function():
    modules = _split_self_tests(SUITE)
    parametrized = [m for m in modules if "def test_parametrized" in m]
    assert len(parametrized) == 1
    assert "@pytest.mark.parametrize" in parametrized[0]


def test_header_is_replicated_into_each_module():
    for module in _split_self_tests(SUITE):
        assert "import impl" in module
        assert "CASES = " in module
        assert "def helper(" in module
        assert "def two()" in module


def test_a_test_class_is_kept_whole():
    suite = "import impl\n\n\nclass TestThing:\n    def test_a(self):\n        assert impl.add(1, 1) == 2\n\n    def test_b(self):\n        assert impl.add(0, 0) == 0\n"
    modules = _split_self_tests(suite)
    assert len(modules) == 1
    assert run_probe(probe_code=modules[0], impl_source=IMPL, timeout_s=40).status is RunStatus.PASS


def test_empty_and_testless_inputs_are_safe():
    assert _split_self_tests("") == []
    assert _split_self_tests("import impl\n") == ["import impl\n"]


def test_unparsable_source_is_passed_through_unchanged():
    broken = "def test_x(:\n    pass\n"
    assert _split_self_tests(broken) == [broken]
