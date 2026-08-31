"""Stage 1 - the Cartographer.

Reads the specification and nothing else, and emits an obligation ledger.

Two mechanical guardrails wrap the model here, and both matter more than the
prompt does:

**Quote verification.**  Every obligation must carry a verbatim contiguous
substring of the specification.  The check is a string containment test after
whitespace normalisation -- no model in the loop -- and a failure is fed back as
a repair instruction naming the offending obligation.  An obligation whose quote
cannot be found is dropped, so a hallucinated requirement cannot become an
accusation later.

**Barrier attestation.**  The exact bytes sent to this stage are hashed and
checked against the implementation source.  If any non-trivial line of the
implementation appears in the context, the run aborts.  The attestation is
written into the trajectory, so the claim "the spec reader never saw the code"
is something a judge can verify rather than take on trust.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..llm.router import LLMRouter
from ..prompts import render
from ..trace.recorder import TrajectoryRecorder
from ..types import Ambiguity, Obligation, ObligationGraph, sha256_text

_WS = re.compile(r"\s+")


class BarrierViolation(RuntimeError):
    """Raised when implementation text is detected inside a spec-only context."""


def _normalise(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


class _CartographerPayload(BaseModel):
    obligations: list[Obligation] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    vocabulary: dict[str, str] = Field(default_factory=dict)


@dataclass
class BarrierAttestation:
    """Evidence that a context contained no implementation text."""

    context_sha256: str
    context_chars: int
    impl_sha256: str
    impl_lines_checked: int
    impl_lines_published_by_spec: int
    leaked_lines: list[str]

    @property
    def clean(self) -> bool:
        return not self.leaked_lines

    def to_dict(self) -> dict:
        return {
            "context_sha256": self.context_sha256,
            "context_chars": self.context_chars,
            "impl_sha256": self.impl_sha256,
            "impl_lines_checked": self.impl_lines_checked,
            "impl_lines_published_by_spec": self.impl_lines_published_by_spec,
            "leaked_lines": self.leaked_lines,
            "clean": self.clean,
        }


def attest_barrier(context: str, impl_src: str, *, spec: str | None = None) -> BarrierAttestation:
    """Check that no *implementation-derived* line of ``impl_src`` is in ``context``.

    Trivial lines (imports, blank, punctuation-only, very short) are excluded
    because they occur by coincidence in unrelated text; a match on them would
    be noise rather than a leak.

    Lines the specification itself publishes are excluded too, and this is the
    substantive point rather than a convenience.  A ticket that says "build
    ``def sort_versions(tags: list[str]) -> list[str]``" has *declared* that
    signature: it is part of the requirement, not something learned from
    reading the code.  The barrier exists to keep out what the implementation
    reveals about its own **behaviour**, so counting the spec's own words as a
    leak would fire on every well-written ticket and say nothing.  Excluding
    them keeps the check discriminating: it stays silent for the real pipeline
    and fires immediately for the ``abl_no_barrier`` configuration, whose
    context genuinely carries the implementation body.
    """
    haystack = _normalise(context)
    published = _normalise(spec) if spec is not None else ""
    leaked: list[str] = []
    checked = 0
    from_spec = 0
    for raw in impl_src.splitlines():
        line = raw.strip()
        if len(line) < 24 or line.startswith(("#", '"""', "'''", "import ", "from ")):
            continue
        normalised = _normalise(line)
        if published and normalised in published:
            from_spec += 1
            continue
        checked += 1
        if normalised in haystack:
            leaked.append(line[:120])
    return BarrierAttestation(
        context_sha256=sha256_text(context),
        context_chars=len(context),
        impl_sha256=sha256_text(impl_src),
        impl_lines_checked=checked,
        impl_lines_published_by_spec=from_spec,
        leaked_lines=leaked[:5],
    )


def verify_quotes(spec: str, graph: ObligationGraph) -> list[str]:
    """Return the ids of obligations whose quote is not in the spec."""
    haystack = _normalise(spec)
    bad: list[str] = []
    for obligation in graph.obligations:
        found = _normalise(obligation.quote) in haystack
        obligation.quote_verified = found
        if not found:
            bad.append(obligation.id)
    return bad


def run_cartographer(
    *,
    spec: str,
    router: LLMRouter,
    recorder: TrajectoryRecorder,
    impl_src: str | None = None,
    max_obligations: int = 10,
) -> tuple[ObligationGraph, BarrierAttestation | None]:
    """Build the obligation ledger from the specification alone."""
    recorder.stage_start("cartographer", "spec-only: the implementation is not in this context")

    system = render("cartographer", max_obligations=max_obligations)
    user = f"# Specification\n\n{spec}"

    attestation: BarrierAttestation | None = None
    if impl_src is not None:
        attestation = attest_barrier(system + "\n" + user, impl_src, spec=spec)
        recorder.tool_call(
            tool="barrier_attest",
            args={"context_chars": len(system) + len(user)},
            result=attestation.to_dict(),
        )
        if not attestation.clean:
            raise BarrierViolation(
                "implementation text found in the spec-only context: "
                + "; ".join(attestation.leaked_lines)
            )

    def _check(payload: _CartographerPayload) -> str | None:
        """Semantic repair hook: reject unverifiable quotes before accepting."""
        haystack = _normalise(spec)
        bad = [o.id for o in payload.obligations if _normalise(o.quote) not in haystack]
        if not bad:
            return None
        offenders = ", ".join(bad[:4])
        return (
            f"These obligations carry a `quote` that is not a verbatim substring of the "
            f"specification: {offenders}. Every quote is checked by exact string match "
            f"after whitespace normalisation. Copy a contiguous span from the specification "
            f"character for character, or delete the obligation."
        )

    payload = router.structured(
        purpose="cartographer",
        system=system,
        user=user,
        schema=_CartographerPayload,
        role="smart",
        max_tokens=6000,
        extra_validate=_check,
    )

    graph = ObligationGraph(
        obligations=payload.obligations,
        ambiguities=payload.ambiguities,
        vocabulary=payload.vocabulary,
        spec_sha256=sha256_text(spec),
    )
    unverified = verify_quotes(spec, graph)
    if unverified:
        recorder.decision(
            what="dropped obligations with unverifiable quotes",
            why="a hallucinated requirement must never become an accusation",
            data={"dropped": unverified},
        )
        graph.obligations = [o for o in graph.obligations if o.quote_verified]

    recorder.stage_end(
        "cartographer",
        {
            "obligations": len(graph.obligations),
            "ambiguities": len(graph.ambiguities),
            "quotes_rejected": len(unverified),
            "barrier_clean": attestation.clean if attestation else None,
        },
    )
    return graph, attestation
