"""Stage 5b - the Oracle: an independent second opinion that never sees the claim.

Why this stage exists
---------------------
The Referee is asked "does the specification require the asserted result rather
than the observed one?", and it is handed the clause the probe was derived from.
That framing anchors it.  On the first live case a probe demanded that
``resolve_range('bytes=500-500', 1)`` return ``[(0, 0)]`` because its clause says
an over-long *last* offset is clamped -- while another paragraph of the same
document says a *first* offset past the end makes the range unsatisfiable, and
spells the asymmetry out in words.  The Referee upheld the accusation with the
clause in front of it, and upheld it again with the entire specification in
front of it.  Being shown the right words was not enough: it had already been
told what the answer was supposed to be.

So this stage removes the claim instead of adding context.  The Oracle sees the
specification and **one concrete call**.  It does not see the clause, the probe,
the implementation, the observed behaviour, or the expectation it is implicitly
being asked to check.  It simply works out what the call should produce.

The adjudication that follows is then **mechanical** -- ``ast.literal_eval`` and
an equality test, with no model deciding anything:

    oracle says raises E     and the probe asserted a value   -> contradiction
    oracle says value V      and the probe asserted value W    -> contradiction iff V != W
    oracle says value V      and the probe asserted raises E   -> contradiction
    oracle says unknown                                        -> defer to the Referee

A contradiction demotes the finding to ``bad_test``.  Agreement leaves the
Referee's verdict alone.  The Oracle can therefore only ever *remove* an
accusation, never manufacture one, which is the correct asymmetry for a stage
whose job is protecting the reader's trust.
"""

from __future__ import annotations

import ast

from pydantic import BaseModel

from ..config import RunConfig
from ..llm.router import LLMRouter
from ..prompts import load as load_prompt
from ..trace.recorder import TrajectoryRecorder
from ..types import Probe, Triage, TriageOutcome


class OraclePrediction(BaseModel):
    kind: str = "unknown"  # "value" | "raises" | "unknown"
    value_repr: str = ""
    exception: str = ""
    reason: str = ""


def asserted_call(probe_code: str, *, entrypoint: str = "") -> str:
    """Extract the call under test from a probe, with ``ast``.

    Returns the first call to the module under test that appears inside an
    assertion or a ``pytest.raises`` block, rendered without the ``impl.``
    prefix so the Oracle sees a plain function call rather than a hint that it
    is auditing somebody's module.
    """
    try:
        tree = ast.parse(probe_code)
    except SyntaxError:
        return ""

    def render(node: ast.AST) -> str | None:
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            func = inner.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id != "impl":
                    continue
                if entrypoint and func.attr != entrypoint:
                    continue
                return ast.unparse(inner).removeprefix("impl.")
        return None

    # Prefer a call written inside the assertion or the `raises` block, since
    # that is unambiguously the call under test.  But probes routinely bind the
    # result first --  `result = impl.f(x)` then `assert result == ...` -- so
    # the whole module is searched as a fallback.  Missing that shape silently
    # disabled this entire stage the first time it ran.
    for finder in (ast.Assert, ast.With):
        for node in ast.walk(tree):
            if isinstance(node, finder):
                rendered = render(node)
                if rendered:
                    return rendered
    return render(tree) or ""


def _literal(text: str) -> tuple[bool, object]:
    try:
        return True, ast.literal_eval(text.strip())
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return False, None


def contradicts(prediction: OraclePrediction, expectation: str) -> tuple[bool, str]:
    """Decide mechanically whether the Oracle disagrees with the probe's claim.

    ``expectation`` is the string produced by
    :func:`blindspot.agents.referee.asserted_expectation`, i.e. ``"== <literal>"``
    or ``"raises <Name>"``.  Anything this function cannot compare with certainty
    is reported as *no contradiction*, so an unparseable claim is left to the
    Referee rather than being silently discarded.
    """
    kind = (prediction.kind or "unknown").strip().lower()
    if kind == "unknown":
        return False, "oracle abstained"

    claim = expectation.strip()
    if claim.startswith("raises "):
        claimed_exception = claim.removeprefix("raises ").strip().split(".")[-1]
        if kind == "raises":
            predicted = prediction.exception.strip().split(".")[-1]
            if predicted and predicted != claimed_exception:
                return True, f"oracle expects {predicted}, the probe demanded {claimed_exception}"
            return False, "oracle agrees an exception is required"
        return True, (
            f"oracle expects the value {prediction.value_repr!r}, "
            f"the probe demanded {claimed_exception}"
        )

    if not claim.startswith("== "):
        return False, "claim is not a simple equality; left to the referee"

    claimed_repr = claim.removeprefix("== ").strip()
    ok_claim, claimed_value = _literal(claimed_repr)
    if not ok_claim:
        return False, "claimed value is not a literal; left to the referee"

    if kind == "raises":
        return True, (
            f"oracle expects {prediction.exception or 'an exception'}, "
            f"the probe demanded the value {claimed_repr}"
        )

    ok_pred, predicted_value = _literal(prediction.value_repr)
    if not ok_pred:
        return False, "oracle's answer is not a literal; left to the referee"

    if predicted_value != claimed_value:
        return True, (f"oracle computes {prediction.value_repr}, the probe demanded {claimed_repr}")
    return False, "oracle agrees with the probe"


def second_opinion(
    *,
    spec: str,
    probe: Probe,
    expectation: str,
    entrypoint: str,
    verdict: Triage,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
) -> Triage:
    """Return ``verdict``, demoted to ``bad_test`` if an independent read disagrees."""
    if not config.oracle or verdict.outcome is not TriageOutcome.UPHELD:
        return verdict

    call = asserted_call(probe.code, entrypoint=entrypoint)
    if not call or not expectation:
        return verdict

    prediction = router.structured(
        purpose="oracle",
        system=load_prompt("oracle"),
        user="\n".join(
            [
                "# Specification",
                "",
                spec,
                "",
                "# The call",
                "",
                "```python",
                call,
                "```",
                "",
                "What does the specification require this call to produce?",
            ]
        ),
        schema=OraclePrediction,
        role="smart",
        # Generous on purpose.  At 1500 the model narrated its way through the
        # specification and was cut off before the closing brace, so the reply
        # contained no parsable JSON at all -- which failed schema repair on 40%
        # of cases and made this stage silently fall back to doing nothing.
        max_tokens=3000,
    )

    disagrees, why = contradicts(prediction, expectation)
    recorder.tool_call(
        tool="oracle.second_opinion",
        args={"call": call, "probe_expectation": expectation},
        result={
            "kind": prediction.kind,
            "value_repr": prediction.value_repr,
            "exception": prediction.exception,
            "reason": prediction.reason[:300],
            "contradicts_probe": disagrees,
            "adjudication": why,
        },
    )
    if not disagrees:
        return verdict

    recorder.decision(
        what=f"demoted {probe.id}: upheld -> bad_test",
        why=f"independent oracle disagreed with the probe's expectation ({why})",
        data={"call": call, "oracle_reason": prediction.reason[:300]},
    )
    return Triage(
        outcome=TriageOutcome.BAD_TEST,
        reason=(
            f"Overturned by an independent reading of the specification that never saw "
            f"this test: {why}. Oracle's reasoning: {prediction.reason}"
        )[:800],
        spec_supports_expectation=False,
    )
