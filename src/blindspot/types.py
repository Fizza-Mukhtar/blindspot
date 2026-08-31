"""Typed contracts for every message that crosses an agent boundary.

Blindspot deliberately has *no* free-text hand-offs between stages.  Every
inter-agent message is a Pydantic model, validated on receipt, with a bounded
repair loop when a model returns something off-schema (see
``blindspot.llm.router.structured``).  That is what makes the pipeline
debuggable: a stage either produced a well-formed artefact or it failed loudly.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --------------------------------------------------------------------------- #
# Stage 1 - the Obligation Graph (produced from the SPEC ALONE)
# --------------------------------------------------------------------------- #


class ObligationKind(str, Enum):
    """Why the obligation exists.  Drives which probe recipes are eligible."""

    MUST = "MUST"  # positive behavioural requirement
    MUST_NOT = "MUST_NOT"  # prohibition
    ERROR = "ERROR"  # required failure mode / exception
    BOUNDARY = "BOUNDARY"  # explicit edge of the input domain
    DEFAULT = "DEFAULT"  # behaviour when an input is omitted
    INVARIANT = "INVARIANT"  # property that must hold for all inputs


class Risk(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Obligation(BaseModel):
    """One atomic, independently testable thing the spec demands."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^OB-\d{3}$")
    kind: ObligationKind
    statement: str = Field(min_length=8, max_length=400)
    quote: str = Field(
        min_length=4,
        description=(
            "Verbatim substring of the spec. Mechanically verified; "
            "hallucinated quotes are rejected and the stage is retried."
        ),
    )
    risk: Risk = Risk.MEDIUM
    inputs_hint: list[str] = Field(
        default_factory=list,
        description="Concrete input shapes worth trying, in the spec's own vocabulary.",
    )
    depends_on_ambiguity: list[str] = Field(default_factory=list)

    # Filled in by the harness, never by the model.
    quote_verified: bool = False


class Ambiguity(BaseModel):
    """Something the spec genuinely does not determine.

    Ambiguities are *never* reported as defects.  They are routed to a human
    decision queue (Rule Book #04/#05) or resolved by a committed policy file.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^AM-\d{3}$")
    question: str = Field(min_length=8, max_length=400)
    options: list[str] = Field(min_length=2, max_length=6)
    quote: str = ""
    why_it_matters: str = ""
    affects: list[str] = Field(default_factory=list)

    resolution: str | None = None
    resolved_by: Literal["human", "policy", "unresolved"] = "unresolved"


class ObligationGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    obligations: list[Obligation] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    vocabulary: dict[str, str] = Field(
        default_factory=dict, description="Domain terms the spec defines or assumes."
    )
    spec_sha256: str = ""

    def resolved_obligations(self) -> list[Obligation]:
        """Obligations that are safe to raise a defect against.

        An obligation blocked on an unresolved ambiguity is excluded: the spec
        does not actually settle the question, so a mismatch is a *question*,
        not a bug.  This single rule is the largest false-alarm reduction in
        the system (see CHANGELOG.md, iteration 5).
        """
        unresolved = {a.id for a in self.ambiguities if a.resolved_by == "unresolved"}
        return [
            o
            for o in self.obligations
            if o.quote_verified and not (set(o.depends_on_ambiguity) & unresolved)
        ]


# --------------------------------------------------------------------------- #
# Stage 2 - Surface map (pure AST, no model involved)
# --------------------------------------------------------------------------- #


class ParamInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    annotation: str | None = None
    default: str | None = None
    kind: str = "positional_or_keyword"


class FunctionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    params: list[ParamInfo] = Field(default_factory=list)
    returns: str | None = None
    docstring: str | None = None
    raises: list[str] = Field(default_factory=list)
    is_async: bool = False


class SurfaceMap(BaseModel):
    """The callable contract of the implementation, extracted with ``ast``.

    This is the *only* implementation-derived information that crosses the
    barrier into the adversary: the adversary must know how to **call** the
    code, but nothing about how it **behaves**.
    """

    model_config = ConfigDict(extra="forbid")

    module: str = ""
    functions: list[FunctionInfo] = Field(default_factory=list)
    classes: list[str] = Field(default_factory=list)
    constants: dict[str, str] = Field(default_factory=dict)
    imports: list[str] = Field(default_factory=list)
    exceptions_defined: list[str] = Field(default_factory=list)

    def render(self) -> str:
        """A compact, deterministic textual rendering for prompts."""
        lines: list[str] = [f"module: {self.module}"]
        for fn in self.functions:
            params = ", ".join(
                p.name
                + (f": {p.annotation}" if p.annotation else "")
                + (f" = {p.default}" if p.default is not None else "")
                for p in fn.params
            )
            ret = f" -> {fn.returns}" if fn.returns else ""
            lines.append(f"def {fn.name}({params}){ret}")
            if fn.docstring:
                first = fn.docstring.strip().splitlines()[0][:160]
                lines.append(f'    """{first}"""')
            if fn.raises:
                lines.append(f"    # documented raises: {', '.join(sorted(set(fn.raises)))}")
        if self.classes:
            lines.append(f"classes: {', '.join(self.classes)}")
        if self.exceptions_defined:
            lines.append(f"exception types defined: {', '.join(self.exceptions_defined)}")
        if self.constants:
            items = ", ".join(f"{k}={v}" for k, v in sorted(self.constants.items()))
            lines.append(f"module constants: {items}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Stage 3/4 - probes and their execution
# --------------------------------------------------------------------------- #


class Strategy(str, Enum):
    EXAMPLE = "example"  # a hand-picked concrete input
    BOUNDARY = "boundary"  # the edge of a stated domain
    PROPERTY = "property"  # Hypothesis, universally quantified
    METAMORPHIC = "metamorphic"  # relation between two calls
    ROUNDTRIP = "roundtrip"  # encode/decode identity


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    obligation_id: str
    strategy: Strategy
    rationale: str = Field(max_length=600)
    code: str = Field(min_length=20, description="A complete, self-contained pytest module.")
    archetype_id: str | None = None  # which memory archetype seeded this probe

    @field_validator("code")
    @classmethod
    def _must_define_a_test(cls, v: str) -> str:
        if "def test_" not in v:
            raise ValueError("probe code must define at least one `test_` function")
        return v


class RunStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"  # collection error, import error, wrong API usage
    TIMEOUT = "timeout"


class ProbeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: RunStatus
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    assertion: str = ""
    failing_input: str = ""
    exit_code: int = 0

    @property
    def is_counterexample(self) -> bool:
        return self.status is RunStatus.FAIL


# --------------------------------------------------------------------------- #
# Stage 5 - triage and findings
# --------------------------------------------------------------------------- #


class TriageOutcome(str, Enum):
    UPHELD = "upheld"  # the observed behaviour really does violate the quote
    BAD_TEST = "bad_test"  # the probe misread the spec; discard
    AMBIGUOUS = "ambiguous"  # route to a human, do not claim a defect
    OUT_OF_DOMAIN = "out_of_domain"  # input outside the spec's stated domain


class Triage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: TriageOutcome
    reason: str = Field(max_length=800)
    spec_supports_expectation: bool = False


class Finding(BaseModel):
    """A single, evidence-backed accusation against the implementation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    obligation_id: str
    title: str = Field(max_length=160)
    spec_quote: str
    minimal_input: str
    expected: str
    actual: str
    repro_test: str
    strategy: Strategy
    triage: Triage
    severity: Risk = Risk.MEDIUM
    shrink_steps: int = 0


class Verdict(str, Enum):
    DEFECT = "DEFECT"
    CLEAN = "CLEAN"
    NEEDS_HUMAN = "NEEDS_HUMAN"


class CostRecord(BaseModel):
    """Accounting for one run.

    ``input_tokens`` / ``output_tokens`` are **content** tokens: an estimate
    derived from the actual prompt and completion text (characters / 4), which
    is the only quantity comparable across backends and the only one
    attributable to Blindspot's own design.

    ``provider_*_tokens`` are whatever the backend billed.  They are kept
    separate because the Claude Code CLI backend wraps every prompt in its own
    harness -- tool schemas, cache blocks -- which added 8k-28k tokens per call
    on the development machine.  That overhead is a property of the transport,
    not of the agent, so folding it into a cost-per-audit figure would overstate
    the price of every system by roughly the same large constant and quietly
    make the comparison meaningless.
    """

    model_config = ConfigDict(extra="forbid")
    calls: int = 0
    input_tokens: int = 0  # content estimate, chars/4
    output_tokens: int = 0  # content estimate, chars/4
    provider_input_tokens: int = 0  # as billed by the backend
    provider_output_tokens: int = 0
    usd: float = 0.0  # priced from the content estimate
    wall_ms: int = 0
    sandbox_runs: int = 0

    def merge(self, other: CostRecord) -> CostRecord:
        return CostRecord(
            calls=self.calls + other.calls,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            provider_input_tokens=self.provider_input_tokens + other.provider_input_tokens,
            provider_output_tokens=self.provider_output_tokens + other.provider_output_tokens,
            usd=round(self.usd + other.usd, 6),
            wall_ms=self.wall_ms + other.wall_ms,
            sandbox_runs=self.sandbox_runs + other.sandbox_runs,
        )


def estimate_tokens(text: str) -> int:
    """Backend-independent token estimate.

    Deliberately crude and deliberately deterministic: four characters per
    token.  Its job is to make cost comparable *between systems in this
    benchmark*, not to predict an invoice, and being a pure function of the
    text means it survives cassette replay unchanged.
    """
    return max(0, (len(text) + 3) // 4)


class AuditReport(BaseModel):
    """The artefact the user actually consumes."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    system: str  # "blindspot" | "baseline_direct" | "baseline_react" | ablation id
    verdict: Verdict
    findings: list[Finding] = Field(default_factory=list)
    open_questions: list[Ambiguity] = Field(default_factory=list)
    obligations_total: int = 0
    obligations_probed: int = 0
    probes_run: int = 0
    probes_discarded: int = 0
    # Accusations the Referee upheld and the independent Oracle then
    # withdrew.  Surfaced because it is the clearest single measure of
    # how much noise adjudication is keeping out of the reader's report.
    withdrawn_by_oracle: int = 0
    cost: CostRecord = Field(default_factory=CostRecord)
    notes: list[str] = Field(default_factory=list)
    error: str | None = None

    def emitted_tests(self) -> list[str]:
        return [f.repro_test for f in self.findings]


# --------------------------------------------------------------------------- #
# Benchmark case description
# --------------------------------------------------------------------------- #


class CaseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    task_id: str
    split: Literal["dev", "test"]
    has_defect: bool
    difficulty: int = Field(ge=1, le=5, default=3)
    trap: str = ""  # human-readable description of the observed defect
    trap_class: str = ""  # taxonomy label, e.g. "boundary/inclusive-range"
    grounding: str = ""  # RFC / standard / CWE the trap is grounded in
    witness_input: str = ""  # an input where impl and reference disagree
    spec_variant: Literal["detailed", "terse"] = "detailed"
    provenance: Literal["forged", "authored"] = "forged"
    # Does the task's authoritative selftest FAIL on this implementation?
    #
    # `has_defect` means "differs from the reference somewhere under differential
    # fuzzing".  That is not the same as "violates the specification": an
    # implementation can differ from one correct reference on inputs the
    # specification never determines.  Measurement showed 13 of 16 buggy cases
    # are exactly that.  This field separates the two, and it is computed by
    # execution (scripts/label_spec_visible.py), never by judgement.
    spec_visible: bool | None = None
    forged_by: str = ""  # model that wrote impl.py + self_tests.py
    self_tests_green: bool = True
    entrypoint: str = ""  # primary public function name
    notes: str = ""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable JSON used for content-addressing.  Sorted keys, no whitespace drift."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
