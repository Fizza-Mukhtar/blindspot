"""Stage 3/4 - the Adversary and its repair loop.

The adversary receives one obligation, its verbatim clause, the callable
surface of the implementation, and any archetypes memory considers relevant.
It never receives the implementation body.

Everything it produces is executed immediately, and the outcome is routed:

    ERROR    the probe could not run -- wrong signature, bad import, a fixture
             that does not exist.  The traceback goes back to the adversary and
             it gets another attempt.  This is a *tool* failure, not evidence.
    PASS     no counterexample on this obligation.  Recorded, not retried:
             re-rolling until something turns red is how false alarms are
             manufactured.
    FAIL     a candidate counterexample.  Handed to the referee.
    TIMEOUT  discarded, with the obligation marked unprobed.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..config import RunConfig
from ..llm.router import LLMRouter
from ..prompts import render
from ..sandbox.runner import run_probe
from ..trace.recorder import TrajectoryRecorder
from ..types import Obligation, Probe, ProbeResult, RunStatus, Strategy, SurfaceMap
from .memory import ArchetypeMemory


class _ProbeSpec(BaseModel):
    obligation_id: str = ""
    strategy: Strategy = Strategy.EXAMPLE
    rationale: str = Field(default="", max_length=600)
    code: str


class _AdversaryPayload(BaseModel):
    probes: list[_ProbeSpec] = Field(default_factory=list)


@dataclass
class ProbeAttempt:
    probe: Probe
    result: ProbeResult
    attempts: int


# Two framings for the same list of attacks.  The default leaves the choice of
# strategy open, and measurement showed what a model does with an open choice:
# 89% of its probes were a single hand-picked input, and only 8% searched the
# input space with `hypothesis`.  Guessing one point in a space with billions of
# them is why the spec-only configuration detected 1 of 9 held-out defects.
#
# SEARCH_FIRST does not give the adversary any more information -- it still
# never sees the implementation body.  It changes what it does with what it has.
GUESS_OK = "Pick whichever attack is most likely to expose a violation of this obligation."

SEARCH_FIRST = """**Search, do not guess.** A single hand-picked input tests one point in a space
with billions of them, and the inputs that break real code are rarely the ones that come
to mind first. Unless this obligation's input domain is genuinely finite and small enough
to enumerate, your probe must **search** it:

- Prefer a `hypothesis` property that quantifies the obligation over a generated domain,
  with `@settings(max_examples=100)` and a strategy tight enough that every generated
  input is actually in the specification's domain.
- Where the obligation relates two calls rather than fixing one value, write the
  metamorphic relation over generated inputs instead (order-independence, idempotence,
  encode-then-decode, a sum preserved).
- Fall back to a single concrete example only when the obligation genuinely names one
  specific input and output, such as a required exception on one malformed value.

You still may not read the implementation, and you still must justify the expected value
from the quoted clause. Searching is about *where you look*, never about *what you expect*."""


def _build_user_prompt(
    *,
    obligation: Obligation,
    surface: SurfaceMap,
    memory_block: str,
    allow_property: bool,
    impl_src: str = "",
) -> str:
    hints = "\n".join(f"- {h}" for h in obligation.inputs_hint) or "- (none supplied)"
    strategies = "example, boundary, property, metamorphic, roundtrip"
    if not allow_property:
        strategies = "example, boundary, metamorphic, roundtrip (property-based probes are disabled for this run)"
    blocks = [
        "# The obligation to falsify",
        "",
        f"id: {obligation.id}",
        f"kind: {obligation.kind.value}",
        f"risk: {obligation.risk.value}",
        f"statement: {obligation.statement}",
        "",
        "## Verbatim clause from the specification",
        "",
        f"> {obligation.quote}",
        "",
        "## Inputs the specification reader thought worth trying",
        "",
        hints,
        "",
        "# Callable surface of the implementation",
        "",
        "```python",
        surface.render(),
        "```",
        "",
        f"Allowed strategies: {strategies}",
    ]
    if impl_src:
        # Reading the code to decide *where to look* is not the same as reading
        # it to decide *what should happen*.  The obligation above came from a
        # spec-only agent whose context is hashed and attested; it is the
        # authority on the expected value and the code cannot revise it.  What
        # the code supplies is the search: which branch is suspicious, which
        # boundary is hard-coded, which input shape is unhandled.
        blocks += [
            "",
            "# The implementation, for choosing inputs ONLY",
            "",
            "```python",
            impl_src,
            "```",
            "",
            "**Read this to decide where to aim, never to decide what is correct.** The "
            "expected value comes from the clause above, which was derived without ever "
            "seeing this code. If the implementation suggests a different answer from the "
            "clause, the clause wins and that disagreement is exactly the probe to write.",
        ]
    if memory_block:
        blocks += ["", memory_block]
    return "\n".join(blocks)


def run_adversary(
    *,
    obligation: Obligation,
    impl_src: str,
    surface: SurfaceMap,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    memory: ArchetypeMemory | None,
    probe_index: int,
) -> list[ProbeAttempt]:
    """Generate, execute and repair probes for one obligation."""
    memory_block = ""
    archetype_id: str | None = None
    if memory is not None and config.memory:
        hits = memory.retrieve(obligation)
        if hits:
            memory_block = memory.render_for(obligation)
            archetype_id = hits[0].id
            recorder.decision(
                what=f"retrieved {len(hits)} archetype(s) for {obligation.id}",
                why="prior failure shapes are cheap hypotheses to test first",
                data={"archetypes": [a.id for a in hits]},
            )

    system = render(
        "adversary",
        probe_count=config.probes_per_obligation,
        search_directive=(
            SEARCH_FIRST if config.prefer_search_probes and config.property_probes else GUESS_OK
        ),
    )
    user = _build_user_prompt(
        obligation=obligation,
        surface=surface,
        memory_block=memory_block,
        allow_property=config.property_probes,
        impl_src=impl_src if config.adversary_sees_impl else "",
    )

    attempts: list[ProbeAttempt] = []
    payload = router.structured(
        purpose="adversary",
        system=system,
        user=user,
        schema=_AdversaryPayload,
        role="smart",
        max_tokens=4000,
    )
    if not payload.probes:
        recorder.decision(
            what=f"no probe generated for {obligation.id}",
            why="the adversary reported that the clause does not determine an expected value",
        )
        return attempts

    for offset, spec in enumerate(payload.probes[: config.probes_per_obligation]):
        probe = Probe(
            id=f"P-{probe_index:03d}-{offset}",
            obligation_id=obligation.id,
            strategy=spec.strategy,
            rationale=spec.rationale,
            code=spec.code,
            archetype_id=archetype_id,
        )
        attempt = _execute_with_repair(
            probe=probe,
            obligation=obligation,
            impl_src=impl_src,
            surface=surface,
            router=router,
            recorder=recorder,
            config=config,
            system=system,
            base_user=user,
        )
        attempts.append(attempt)
    return attempts


def _execute_with_repair(
    *,
    probe: Probe,
    obligation: Obligation,
    impl_src: str,
    surface: SurfaceMap,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    config: RunConfig,
    system: str,
    base_user: str,
) -> ProbeAttempt:
    current = probe
    result = ProbeResult(status=RunStatus.ERROR)

    for attempt in range(1, config.repair_attempts + 2):
        result = run_probe(
            probe_code=current.code,
            impl_source=impl_src,
            timeout_s=config.sandbox_timeout_s,
        )
        recorder.tool_call(
            tool="sandbox.run_probe",
            args={"probe_id": current.id, "obligation": obligation.id, "code": current.code},
            result={
                "status": result.status.value,
                "assertion": result.assertion,
                "failing_input": result.failing_input,
                "stdout": result.stdout[-1500:],
                "duration_ms": result.duration_ms,
            },
        )

        if result.status is not RunStatus.ERROR:
            break
        if attempt > config.repair_attempts:
            recorder.decision(
                what=f"discarded probe {current.id}",
                why="probe never became runnable within the repair budget",
            )
            break

        recorder.retry(
            reason="probe_not_runnable",
            attempt=attempt,
            detail=(result.stdout or result.stderr)[-1200:],
        )
        repaired = router.structured(
            purpose="adversary",
            system=system,
            user=(
                f"{base_user}\n\n"
                "--- YOUR PREVIOUS PROBE DID NOT RUN ---\n"
                "```python\n"
                f"{current.code}\n"
                "```\n\n"
                "pytest output:\n"
                "```\n"
                f"{(result.stdout or result.stderr)[-2000:]}\n"
                "```\n\n"
                "This is a fault in the probe, not evidence about the implementation. "
                "Fix how the probe calls the code and reply with the corrected probe in "
                "the same JSON format. Keep the same obligation and the same intent."
            ),
            schema=_AdversaryPayload,
            role="smart",
            max_tokens=4000,
        )
        if not repaired.probes:
            break
        spec = repaired.probes[0]
        current = Probe(
            id=current.id,
            obligation_id=obligation.id,
            strategy=spec.strategy,
            rationale=spec.rationale or current.rationale,
            code=spec.code,
            archetype_id=current.archetype_id,
        )

    return ProbeAttempt(probe=current, result=result, attempts=1)
