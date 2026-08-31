"""Orchestration: the Blindspot audit pipeline.

    SPEC.md ──► Cartographer ──► Obligation ledger ──► Ambiguity gate ──┐
                (spec only)         (quotes verified)   (human/policy)  │
                                                                        ▼
    impl.py ──► Surface map ──────────────────────────────► Adversary (fan-out)
                (ast, no model)                                  │
                                                                 ▼
                                                            Sandbox
                                                                 │
                                        ERROR ──► repair ────────┤
                                        PASS  ──► recorded, not retried
                                        FAIL  ──► Referee ──► Minimiser ──► Finding
                                                                 │
                                                                 ▼
                                                            AUDIT.md + repro tests

Every arrow is a validated Pydantic message and every box is logged to the
trajectory.  The flags on :class:`~blindspot.config.RunConfig` switch individual
boxes off, which is how each component's contribution becomes a measured number
in the changelog instead of a claim in the README.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from ..config import RunConfig
from ..llm.router import LLMRouter
from ..trace.recorder import TrajectoryRecorder
from ..types import (
    Ambiguity,
    AuditReport,
    Finding,
    Obligation,
    ObligationGraph,
    Probe,
    ProbeResult,
    Risk,
    RunStatus,
    Triage,
    TriageOutcome,
    Verdict,
)
from .adversary import ProbeAttempt, run_adversary
from .cartographer import BarrierAttestation, run_cartographer
from .memory import ArchetypeMemory
from .oracle import second_opinion
from .referee import asserted_expectation, minimise, triage
from .surface import extract_surface


@dataclass
class AuditArtefacts:
    """Everything a run produced, including the parts the report summarises away."""

    report: AuditReport
    graph: ObligationGraph = field(default_factory=ObligationGraph)
    attempts: list[ProbeAttempt] = field(default_factory=list)
    attestation: BarrierAttestation | None = None


def _apply_decisions(
    graph: ObligationGraph,
    decisions: dict[str, str],
    recorder: TrajectoryRecorder,
) -> None:
    """Resolve ambiguities from a committed policy, else leave them for a human."""
    from ..decisions import question_key

    for ambiguity in graph.ambiguities:
        key = question_key(ambiguity.question)
        resolution = decisions.get(key)
        if resolution:
            ambiguity.resolution = resolution
            ambiguity.resolved_by = "policy"
        recorder.human_checkpoint(
            question=ambiguity.question,
            options=ambiguity.options,
            resolution=ambiguity.resolution,
            resolved_by=ambiguity.resolved_by,
        )


def _selected_obligations(
    graph: ObligationGraph, config: RunConfig, recorder: TrajectoryRecorder
) -> list[Obligation]:
    if config.ambiguity_gate:
        selected = graph.resolved_obligations()
        blocked = [o.id for o in graph.obligations if o not in selected]
        if blocked:
            recorder.decision(
                what=f"withheld {len(blocked)} obligation(s) from probing",
                why=(
                    "they depend on an ambiguity the specification does not settle; "
                    "an unsettled question is escalated to a human, never reported as a defect"
                ),
                data={"withheld": blocked},
            )
    else:
        # Ablation: probe everything, including the genuinely under-determined.
        selected = [o for o in graph.obligations if o.quote_verified]

    risk_order = {Risk.HIGH: 0, Risk.MEDIUM: 1, Risk.LOW: 2}
    selected.sort(key=lambda o: (risk_order.get(o.risk, 1), o.id))
    return selected[: config.max_obligations]


def audit(
    *,
    case_id: str,
    spec: str,
    impl_src: str,
    config: RunConfig,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    memory: ArchetypeMemory | None = None,
    decisions: dict[str, str] | None = None,
    system_name: str = "blindspot",
    entrypoint: str = "",
) -> AuditArtefacts:
    """Run the full pipeline over one (specification, implementation) pair."""
    started = time.monotonic()
    recorder.run_start(
        config={
            "fingerprint": config.fingerprint(),
            "provider": config.provider,
            "models": {"fast": config.resolve("fast"), "smart": config.resolve("smart")},
            "ablations": config.ablation_flags(),
        },
        inputs={"case_id": case_id, "spec_chars": len(spec), "impl_chars": len(impl_src)},
    )

    # ---- Stage 1: obligations from the specification ---------------------- #
    graph, attestation = run_cartographer(
        spec=spec,
        router=router,
        recorder=recorder,
        # Ablation B ("roles, not information"): the Cartographer remains a
        # separate agent with its own instructions, but the implementation is
        # placed in its context.  Passing impl_src here ALSO switches on the
        # attestation check, so the barrier is only asserted when it is enforced.
        impl_src=impl_src if config.information_barrier else None,
        max_obligations=config.max_obligations,
    )
    if not config.information_barrier:
        graph = _rebuild_without_barrier(
            spec=spec,
            impl_src=impl_src,
            router=router,
            recorder=recorder,
            config=config,
        )

    # ---- Stage 2: the human checkpoint ------------------------------------ #
    recorder.stage_start("ambiguity_gate")
    _apply_decisions(graph, decisions or {}, recorder)
    selected = _selected_obligations(graph, config, recorder)
    open_questions = [a for a in graph.ambiguities if a.resolved_by == "unresolved"]
    recorder.stage_end(
        "ambiguity_gate",
        {"selected": len(selected), "open_questions": len(open_questions)},
    )

    # ---- Stage 3: callable surface (deterministic tool) -------------------- #
    recorder.stage_start("surface_map")
    surface = extract_surface(impl_src, include_docstrings=config.surface_docstrings)
    recorder.tool_call(
        tool="ast.extract_surface",
        args={"impl_chars": len(impl_src), "include_docstrings": config.surface_docstrings},
        result={"functions": [f.name for f in surface.functions], "rendered": surface.render()},
    )
    recorder.stage_end("surface_map", {"functions": len(surface.functions)})

    # ---- Stage 4: adversary fan-out --------------------------------------- #
    recorder.stage_start("adversary", f"{len(selected)} obligation(s)")
    attempts: list[ProbeAttempt] = []

    def probe_one(pair: tuple[int, Obligation]) -> list[ProbeAttempt]:
        index, obligation = pair
        return run_adversary(
            obligation=obligation,
            impl_src=impl_src,
            surface=surface,
            router=router,
            recorder=recorder,
            config=config,
            memory=memory,
            probe_index=index,
        )

    if selected:
        with ThreadPoolExecutor(max_workers=max(1, config.concurrency)) as pool:
            for batch in pool.map(probe_one, list(enumerate(selected, start=1))):
                attempts.extend(batch)
    recorder.stage_end(
        "adversary",
        {
            "probes": len(attempts),
            "red": sum(1 for a in attempts if a.result.status is RunStatus.FAIL),
            "green": sum(1 for a in attempts if a.result.status is RunStatus.PASS),
            "unrunnable": sum(1 for a in attempts if a.result.status is RunStatus.ERROR),
        },
    )

    # ---- Stage 5: adjudication -------------------------------------------- #
    recorder.stage_start("referee")
    by_id = {o.id: o for o in selected}
    findings: list[Finding] = []
    escalations: list[Ambiguity] = []
    discarded = 0
    withdrawn = 0

    for attempt in attempts:
        if attempt.result.status is not RunStatus.FAIL:
            if attempt.result.status is not RunStatus.PASS:
                discarded += 1
            continue
        obligation = by_id.get(attempt.probe.obligation_id)
        if obligation is None:
            # The adversary attributed the probe to an obligation that was not
            # in its brief; without a clause to adjudicate against there is
            # nothing sound to say, so it is dropped rather than guessed at.
            discarded += 1
            continue

        verdict = triage(
            spec=spec,
            obligation=obligation,
            probe=attempt.probe,
            result=attempt.result,
            router=router,
            recorder=recorder,
            config=config,
        )
        if verdict.outcome is TriageOutcome.AMBIGUOUS:
            escalations.append(
                Ambiguity(
                    id=f"AM-9{len(escalations):02d}",
                    question=(
                        f"{obligation.statement} -- on input "
                        f"{attempt.result.failing_input or 'see repro test'}, "
                        "which behaviour did you intend?"
                    ),
                    options=[
                        "the specification's literal reading",
                        "the implementation's behaviour",
                    ],
                    quote=obligation.quote,
                    why_it_matters=verdict.reason,
                    affects=[obligation.id],
                )
            )
            discarded += 1
            continue
        if verdict.outcome is not TriageOutcome.UPHELD:
            discarded += 1
            continue

        probe, minimal_input, shrink_steps = minimise(
            probe=attempt.probe,
            result=attempt.result,
            impl_src=impl_src,
            router=router,
            recorder=recorder,
            config=config,
        )

        # Stage 5b: an independent reading that never saw the accusation.  The
        # Referee is handed the clause and the claim together, which anchors it;
        # the Oracle is handed the specification and one call, and can only ever
        # withdraw a finding, never create one.
        #
        # This runs *after* minimisation on purpose.  A pre-minimisation probe
        # often exercises several inputs, and the first call in its source is
        # frequently a worked example from the specification rather than the one
        # that actually failed -- the Oracle's first live run duly adjudicated
        # the wrong call and agreed with it.  The minimised probe is the single
        # failing call, so there is nothing to mistake it for.
        verdict = second_opinion(
            spec=spec,
            probe=probe,
            expectation=asserted_expectation(probe.code),
            entrypoint=entrypoint,
            verdict=verdict,
            router=router,
            recorder=recorder,
            config=config,
        )
        if verdict.outcome is not TriageOutcome.UPHELD:
            discarded += 1
            withdrawn += 1
            continue

        findings.append(
            _build_finding(
                index=len(findings) + 1,
                obligation=obligation,
                probe=probe,
                result=attempt.result,
                verdict=verdict,
                minimal_input=minimal_input,
                shrink_steps=shrink_steps,
            )
        )

    recorder.stage_end(
        "referee",
        {
            "findings": len(findings),
            "discarded": discarded,
            "escalated": len(escalations),
            "withdrawn_by_oracle": withdrawn,
        },
    )

    # ---- Stage 6: the report ---------------------------------------------- #
    verdict_value = (
        Verdict.DEFECT
        if findings
        else (Verdict.NEEDS_HUMAN if (open_questions or escalations) else Verdict.CLEAN)
    )
    cost = router.cost
    cost.wall_ms = int((time.monotonic() - started) * 1000)
    cost.sandbox_runs = len(attempts)

    report = AuditReport(
        case_id=case_id,
        system=system_name,
        verdict=verdict_value,
        findings=findings,
        open_questions=open_questions + escalations,
        obligations_total=len(graph.obligations),
        obligations_probed=len(selected),
        probes_run=len(attempts),
        probes_discarded=discarded,
        withdrawn_by_oracle=withdrawn,
        cost=cost,
    )
    recorder.run_end(
        verdict=verdict_value.value,
        findings=len(findings),
        cost=cost.model_dump(),
    )
    return AuditArtefacts(report=report, graph=graph, attempts=attempts, attestation=attestation)


def _rebuild_without_barrier(
    *,
    spec: str,
    impl_src: str,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
) -> ObligationGraph:
    """Ablation B: the same Cartographer role, with the implementation in context.

    This is the comparison the project's central claim rests on.  The agent
    architecture is unchanged -- a dedicated spec-reading agent with its own
    instructions, its own schema and its own quote verification -- and the only
    difference is that ``impl.py`` is appended to its context.  Whatever the
    detection rate does between here and the barrier configuration is the value
    of the information boundary, separated from the value of having a separate
    role at all.
    """
    from ..prompts import render
    from ..types import sha256_text
    from .cartographer import _CartographerPayload, attest_barrier, verify_quotes

    recorder.stage_start(
        "cartographer", "ABLATION: barrier removed -- implementation is in this context"
    )
    system = render("cartographer", max_obligations=config.max_obligations)
    user = (
        f"# Specification\n\n{spec}\n\n"
        f"# Implementation under review (`impl.py`)\n\n```python\n{impl_src}\n```"
    )

    # Positive control.  The same attestation that stays silent for the real
    # pipeline is run here, where it is *expected* to fire, and its verdict is
    # written into the trajectory.  A check that never fails is not evidence;
    # this is what shows the barrier attestation can tell the two apart.
    attestation = attest_barrier(system + "\n" + user, impl_src, spec=spec)
    recorder.tool_call(
        tool="barrier_attest",
        args={"context_chars": len(system) + len(user), "expected_to_fail": True},
        result=attestation.to_dict(),
    )

    payload = router.structured(
        purpose="cartographer",
        system=system,
        user=user,
        schema=_CartographerPayload,
        role="smart",
        max_tokens=6000,
    )
    graph = ObligationGraph(
        obligations=payload.obligations,
        ambiguities=payload.ambiguities,
        vocabulary=payload.vocabulary,
        spec_sha256=sha256_text(spec),
    )
    verify_quotes(spec, graph)
    graph.obligations = [o for o in graph.obligations if o.quote_verified]
    recorder.stage_end(
        "cartographer",
        {
            "obligations": len(graph.obligations),
            "ambiguities": len(graph.ambiguities),
            "barrier_clean": False,
        },
    )
    return graph


def _build_finding(
    *,
    index: int,
    obligation: Obligation,
    probe: Probe,
    result: ProbeResult,
    verdict: Triage,
    minimal_input: str,
    shrink_steps: int,
) -> Finding:
    expected, actual = _split_assertion(result.assertion, probe.code)
    return Finding(
        id=f"F-{index:02d}",
        obligation_id=obligation.id,
        title=obligation.statement[:160],
        spec_quote=obligation.quote,
        minimal_input=minimal_input or result.failing_input or "(see the repro test)",
        expected=expected,
        actual=actual,
        repro_test=probe.code,
        strategy=probe.strategy,
        triage=verdict,
        severity=obligation.risk,
        shrink_steps=shrink_steps,
    )


def _split_assertion(assertion: str, probe_code: str = "") -> tuple[str, str]:
    """Pull ``expected`` and ``actual`` out of a failure.

    A comparison failure carries both halves in the assertion line.  A failure
    by *raised exception* carries only the observed half, and the earlier code
    filled both fields from it -- so a report could claim the implementation
    "expected X, produced X", which reads as nonsense and hid a real triage
    error on the first live case.  When the assertion line has no comparison,
    the expectation is recovered from the probe's own assert statements
    instead, and only the observation comes from the failure.
    """
    fallback = asserted_expectation(probe_code) if probe_code else ""
    if not assertion:
        return (fallback or "see the repro test", "see the repro test")
    body = assertion.removeprefix("assert ").strip()
    for operator in (" == ", " != ", " < ", " > ", " <= ", " >= "):
        if operator in body:
            left, _, right = body.partition(operator)
            return (right.strip()[:400], left.strip()[:400])
    return (fallback or "see the repro test", assertion[:400])
