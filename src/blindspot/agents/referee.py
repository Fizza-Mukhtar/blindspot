"""Stage 5 - the Referee.

A red test is not a defect.  It is a *claim* that the implementation violates a
clause, and claims need adjudication before they reach a human.

The referee is deliberately the narrowest agent in the system.  It sees the
specification, the clause, the input and the observed failure -- not the
probe's source, and not the implementation.

The specification is present in full, and that is a correction rather than an
oversight.  Adjudicating against a *single* clause let a probe pick an input
whose trigger one clause matches while a different clause overrides it: on the
first live case a probe demanded that `bytes=500-500` clamp to `[(0, 0)]`,
which the clause it was derived from does say, while another clause makes that
range unsatisfiable outright.  Shown one line, the referee upheld a false
accusation; the authority is the document, not the sentence.  What stays
withheld is what would let it rationalise -- the implementation and the probe's
own reasoning.  Both omissions are load-bearing: shown the probe, a model
agrees with the probe's reasoning; shown the implementation, it rationalises the
implementation's behaviour.  Stripped of both, the only question left is the one
that actually matters -- *does this clause require that result on this input?*

Its calibration is asymmetric on purpose.  Missing a defect costs one finding;
a false accusation costs the reader's trust in every other finding in the
report, which is the difference between a tool someone uses and a tool someone
turns off.
"""

from __future__ import annotations

import ast
import re

from pydantic import BaseModel

from ..config import RunConfig
from ..llm.router import LLMRouter
from ..prompts import load as load_prompt
from ..sandbox.runner import run_probe
from ..trace.recorder import TrajectoryRecorder
from ..types import Obligation, Probe, ProbeResult, RunStatus, Triage, TriageOutcome

_E_LINE = re.compile(r"(?m)^E\s+(.*)$")
_FALSIFYING = re.compile(r"(?s)Falsifying example:.*?(?=\n\n|\Z)")


class _TriagePayload(BaseModel):
    outcome: TriageOutcome
    reason: str = ""
    spec_supports_expectation: bool = False


class _MinimalPayload(BaseModel):
    code: str
    minimal_input: str = ""


def asserted_expectation(probe_code: str, *, limit: int = 400) -> str:
    """Render *what the test claimed should happen*, with ``ast``, not a model.

    The referee is asked whether the specification requires the asserted result
    rather than the observed one, so it has to be told what was asserted.  When
    a probe fails by *raising*, the captured failure output contains only the
    exception -- the claim itself never appears in it, and the referee was
    being asked to compare an observation against nothing.  That is how a
    confident wrong accusation got upheld on the first live case.

    This extracts only the claim (the right-hand side of an equality, or the
    exception type a ``pytest.raises`` block demanded), never the reasoning
    that produced it, so the referee's information discipline is unchanged.
    """
    try:
        tree = ast.parse(probe_code)
    except SyntaxError:
        return ""

    claims: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare):
            compare = node.test
            if len(compare.ops) == 1 and isinstance(compare.ops[0], ast.Eq):
                claims.append(f"== {ast.unparse(compare.comparators[0])}")
            else:
                claims.append(ast.unparse(compare))
        elif isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "raises"
                    and call.args
                ):
                    claims.append(f"raises {ast.unparse(call.args[0])}")

    seen: list[str] = []
    for claim in claims:
        if claim not in seen:
            seen.append(claim)
    return "; ".join(seen)[:limit]


def failure_evidence(result: ProbeResult, *, limit: int = 1800) -> str:
    """The observable part of a pytest failure, with the test source removed.

    Only the ``E`` lines and any Hypothesis falsifying example survive.  That is
    what keeps the referee's promise -- it sees the observation, never the
    argument that produced it.
    """
    lines = [f"E {line}" for line in _E_LINE.findall(result.stdout + result.stderr)]
    blob = "\n".join(lines)
    falsifying = _FALSIFYING.search(result.stdout)
    if falsifying:
        blob = f"{falsifying.group(0).strip()}\n{blob}"
    return (blob or result.assertion or "(no assertion output captured)")[:limit]


def triage(
    *,
    obligation: Obligation,
    probe: Probe,
    result: ProbeResult,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    spec: str = "",
) -> Triage:
    """Decide whether a red probe is evidence of a defect."""
    if not config.referee:
        # Ablation: accept every red probe.  Retained so the cost of removing
        # adjudication is a measured number rather than an assertion.
        return Triage(
            outcome=TriageOutcome.UPHELD,
            reason="referee disabled for this configuration",
            spec_supports_expectation=True,
        )

    evidence = failure_evidence(result)
    user = "\n".join(
        [
            "# Obligation",
            "",
            f"{obligation.id} ({obligation.kind.value}): {obligation.statement}",
            "",
            "## Verbatim clause",
            "",
            f"> {obligation.quote}",
            "",
            "# The test's stated intent",
            "",
            probe.rationale or "(none stated)",
            "",
            "# The specification (the authority)",
            "",
            spec if (spec and config.referee_full_spec) else "(only the clause above was supplied)",
            "",
            "# Concrete input",
            "",
            result.failing_input or "(not separately captured; see the failure output)",
            "",
            "# What the test asserted should happen",
            "",
            asserted_expectation(probe.code) or "(not mechanically extractable)",
            "",
            "# Failure output",
            "",
            "```",
            evidence,
            "```",
        ]
    )

    payload = router.structured(
        purpose="referee",
        system=load_prompt("referee"),
        user=user,
        schema=_TriagePayload,
        role="smart",
        max_tokens=1200,
    )
    verdict = Triage(
        outcome=payload.outcome,
        reason=payload.reason,
        spec_supports_expectation=payload.spec_supports_expectation,
    )
    recorder.decision(
        what=f"triage {probe.id} -> {verdict.outcome.value}",
        why=verdict.reason[:300],
        data={"obligation": obligation.id, "strategy": probe.strategy.value},
    )
    return verdict


def minimise(
    *,
    probe: Probe,
    result: ProbeResult,
    impl_src: str,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    threshold: int = 90,
) -> tuple[Probe, str, int]:
    """Shrink a failing input, keeping the reduction only if it still fails.

    The model proposes; execution disposes.  A proposed minimal probe is
    accepted only when it is still red on the same implementation, so this stage
    can improve the evidence but can never invent it.  Probes whose input is
    already short skip the call entirely -- Hypothesis has usually shrunk them
    already.
    """
    if not config.shrink:
        return probe, result.failing_input, 0

    current_input = result.failing_input or ""
    if len(probe.code) < 400 and len(current_input) < threshold:
        return probe, current_input, 0

    payload = router.structured(
        purpose="minimise",
        system=load_prompt("minimise"),
        user=(
            "# The failing probe\n\n```python\n"
            f"{probe.code}\n```\n\n"
            "# Its failure output\n\n```\n"
            f"{failure_evidence(result)}\n```\n"
        ),
        schema=_MinimalPayload,
        role="fast",
        max_tokens=2000,
    )
    candidate = Probe(
        id=probe.id,
        obligation_id=probe.obligation_id,
        strategy=probe.strategy,
        rationale=probe.rationale,
        code=payload.code,
        archetype_id=probe.archetype_id,
    )
    check = run_probe(
        probe_code=candidate.code, impl_source=impl_src, timeout_s=config.sandbox_timeout_s
    )
    recorder.tool_call(
        tool="sandbox.run_probe",
        args={"probe_id": probe.id, "purpose": "verify_minimisation", "code": candidate.code},
        result={"status": check.status.value, "assertion": check.assertion},
    )
    if check.status is not RunStatus.FAIL:
        recorder.decision(
            what=f"kept the original probe {probe.id}",
            why="the proposed minimisation stopped reproducing the failure",
        )
        return probe, current_input, 0
    return candidate, (payload.minimal_input or check.failing_input or current_input), 1
