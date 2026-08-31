"""The two baselines the competition brief asks for, implemented honestly.

The brief names "one direct prompt with basic instructions" and "one general
purpose agent with basic tools".  Both are built here, and both are given the
*same* task, the *same* evaluation cases and, deliberately, **more information
than Blindspot gets**: they see the implementation body, which the Blindspot
Cartographer never does.

That asymmetry is the point.  If a system with strictly more context loses, the
difference cannot be explained by access to information, only by what was done
with it.  Token and call parity is measured rather than assumed, and reported
in ``results/parity.json``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..config import RunConfig
from ..llm.router import LLMRouter
from ..prompts import render
from ..sandbox.runner import run_probe
from ..trace.recorder import TrajectoryRecorder
from ..types import (
    AuditReport,
    CostRecord,
    Finding,
    Risk,
    Strategy,
    Triage,
    TriageOutcome,
    Verdict,
)


class _Test(BaseModel):
    name: str = "test_unnamed"
    reason: str = ""
    code: str


class _DirectPayload(BaseModel):
    tests: list[_Test] = Field(default_factory=list)


class _AgentPayload(BaseModel):
    thought: str = ""
    tool: str = "report"
    tests: list[_Test] = Field(default_factory=list)


@dataclass
class BaselineResult:
    report: AuditReport
    tests: list[str] = field(default_factory=list)


def _finding_from_test(
    index: int, test: _Test, *, assertion: str = "", failing_input: str = ""
) -> Finding:
    return Finding(
        id=f"F-{index:02d}",
        obligation_id="-",
        title=(test.reason or test.name)[:160],
        spec_quote="(baseline: no obligation ledger)",
        minimal_input=failing_input or "(see the repro test)",
        expected="see the repro test",
        actual=assertion or "see the repro test",
        repro_test=test.code,
        strategy=Strategy.EXAMPLE,
        triage=Triage(
            outcome=TriageOutcome.UPHELD,
            reason="baseline systems do not adjudicate their own findings",
            spec_supports_expectation=True,
        ),
        severity=Risk.MEDIUM,
    )


# --------------------------------------------------------------------------- #
# B0 -- one direct prompt, no execution
# --------------------------------------------------------------------------- #


def run_direct(
    *,
    case_id: str,
    spec: str,
    impl_src: str,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    max_tests: int = 6,
    system_name: str = "baseline_direct",
) -> BaselineResult:
    """One call, no tools, no feedback.  The floor of the comparison."""
    recorder.run_start(
        config={"system": system_name, "fingerprint": config.fingerprint()},
        inputs={"case_id": case_id, "spec_chars": len(spec), "impl_chars": len(impl_src)},
    )
    recorder.stage_start("direct_prompt")

    payload = router.structured(
        purpose="baseline_direct",
        system=render("baseline_direct", max_tests=max_tests),
        user=(
            f"# Ticket\n\n{spec}\n\n"
            f"# Implementation under review (`impl.py`)\n\n```python\n{impl_src}\n```"
        ),
        schema=_DirectPayload,
        role="smart",
        max_tokens=8000,
    )
    tests = payload.tests[:max_tests]
    findings = [_finding_from_test(i + 1, t) for i, t in enumerate(tests)]

    cost = router.cost
    report = AuditReport(
        case_id=case_id,
        system=system_name,
        verdict=Verdict.DEFECT if findings else Verdict.CLEAN,
        findings=findings,
        probes_run=0,
        cost=cost,
        notes=["one call, no execution, no adjudication"],
    )
    recorder.stage_end("direct_prompt", {"tests": len(tests)})
    recorder.run_end(verdict=report.verdict.value, findings=len(findings), cost=cost.model_dump())
    return BaselineResult(report=report, tests=[t.code for t in tests])


# --------------------------------------------------------------------------- #
# B1 -- a general-purpose agent with a sandbox
# --------------------------------------------------------------------------- #


def run_agent(
    *,
    case_id: str,
    spec: str,
    impl_src: str,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    max_rounds: int = 6,
    max_tests: int = 6,
    system_name: str = "baseline_agent",
) -> BaselineResult:
    """A ReAct-style loop with one tool: run tests against the implementation.

    This is the strong baseline.  It has the implementation body, an execution
    oracle, and several rounds to use them -- the setup most people would reach
    for, and the one Blindspot has to beat to have said anything.
    """
    recorder.run_start(
        config={
            "system": system_name,
            "fingerprint": config.fingerprint(),
            "max_rounds": max_rounds,
        },
        inputs={"case_id": case_id, "spec_chars": len(spec), "impl_chars": len(impl_src)},
    )

    system = render("baseline_agent", max_rounds=max_rounds)
    transcript = (
        f"# Ticket\n\n{spec}\n\n"
        f"# Implementation under review (`impl.py`)\n\n```python\n{impl_src}\n```\n\n"
        "Begin. Reply with a single JSON object."
    )
    reported: list[_Test] = []
    observations: list[str] = []
    sandbox_runs = 0

    for round_index in range(1, max_rounds + 1):
        recorder.stage_start(f"round_{round_index}")
        payload = router.structured(
            purpose="baseline_agent",
            system=system,
            user=transcript,
            schema=_AgentPayload,
            role="smart",
            max_tokens=8000,
        )
        recorder.decision(
            what=f"round {round_index}: {payload.tool}",
            why=payload.thought[:400],
            data={"tests": len(payload.tests)},
        )

        if payload.tool == "report" or round_index == max_rounds:
            reported = payload.tests[:max_tests]
            recorder.stage_end(f"round_{round_index}", {"reported": len(reported)})
            break

        results: list[dict[str, str]] = []
        for test in payload.tests[:max_tests]:
            outcome = run_probe(
                probe_code=test.code,
                impl_source=impl_src,
                timeout_s=config.sandbox_timeout_s,
            )
            sandbox_runs += 1
            recorder.tool_call(
                tool="run_tests",
                args={"name": test.name, "code": test.code},
                result={
                    "status": outcome.status.value,
                    "assertion": outcome.assertion,
                    "stdout": outcome.stdout[-1200:],
                },
            )
            results.append(
                {
                    "name": test.name,
                    "status": outcome.status.value,
                    "output": (outcome.assertion or outcome.stdout[-600:] or "")[:600],
                }
            )
        observations.append(json.dumps(results, indent=2))
        transcript = (
            f"# Ticket\n\n{spec}\n\n"
            f"# Implementation under review (`impl.py`)\n\n```python\n{impl_src}\n```\n\n"
            "# Your previous tool calls and their results\n\n"
            + "\n\n".join(f"```json\n{obs}\n```" for obs in observations[-3:])
            + f"\n\nYou have {max_rounds - round_index} tool call(s) left. "
            "Reply with a single JSON object."
        )
        recorder.stage_end(f"round_{round_index}", {"executed": len(results)})

    findings = [_finding_from_test(i + 1, t) for i, t in enumerate(reported)]
    cost: CostRecord = router.cost
    cost.sandbox_runs = sandbox_runs
    report = AuditReport(
        case_id=case_id,
        system=system_name,
        verdict=Verdict.DEFECT if findings else Verdict.CLEAN,
        findings=findings,
        probes_run=sandbox_runs,
        cost=cost,
        notes=[f"react loop, {max_rounds} rounds, execution feedback, no adjudication"],
    )
    recorder.run_end(verdict=report.verdict.value, findings=len(findings), cost=cost.model_dump())
    return BaselineResult(report=report, tests=[t.code for t in reported])
