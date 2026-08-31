"""The evaluation harness: run every system over every case and grade it.

Systems under evaluation
------------------------
``self_tests``        the case's own model-written suite.  Scores 0 by
                      construction on every buggy case -- that is the failure
                      this project exists to measure, and stating it as a
                      measured floor rather than a rhetorical claim is what
                      makes the benchmark non-trivial.
``baseline_direct``   one prompt, no tools, no feedback.
``baseline_agent``    a general-purpose agent with a sandbox and several rounds.
``blindspot``         the full pipeline.
``abl_*``             Blindspot with exactly one component removed.

Everything shares one cassette store, so a component that does not change a
prompt costs nothing to re-evaluate, and a full ablation sweep replays offline
in seconds.
"""

from __future__ import annotations

import ast
import json
import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from ..agents.adjudicate import adjudicate_tests
from ..agents.memory import ArchetypeMemory
from ..agents.pipeline import audit
from ..baselines.runners import run_agent, run_direct
from ..config import RunConfig
from ..corpus import Case
from ..decisions import load_decisions
from ..llm.base import BaseProvider
from ..llm.cassette import CassetteStore
from ..llm.router import LLMRouter, build_provider, set_inflight_limit
from ..sandbox.runner import run_probe
from ..trace.recorder import TrajectoryRecorder
from ..types import AuditReport, Verdict
from .grader import CaseGrade, grade_case


@dataclass(frozen=True)
class SystemSpec:
    """One configuration under evaluation."""

    name: str
    label: str
    description: str
    kind: str  # "blindspot" | "direct" | "agent" | "self_tests"
    overrides: dict[str, object]


SYSTEMS: dict[str, SystemSpec] = {
    "self_tests": SystemSpec(
        name="self_tests",
        label="The model's own test suite",
        description="The tests the implementing model wrote for its own code. The floor.",
        kind="self_tests",
        overrides={},
    ),
    "baseline_direct": SystemSpec(
        name="baseline_direct",
        label="Baseline A: one direct prompt",
        description="Spec + implementation + 'write tests that find bugs'. One call, no execution.",
        kind="direct",
        overrides={},
    ),
    "baseline_agent": SystemSpec(
        name="baseline_agent",
        label="Baseline B: general agent with tools",
        description="ReAct loop with a sandbox, six rounds, sees the implementation body.",
        kind="agent",
        overrides={},
    ),
    "blindspot": SystemSpec(
        name="blindspot",
        label="Blindspot",
        description="Information barrier, obligation ledger, ambiguity gate, adversary, referee.",
        kind="blindspot",
        overrides={},
    ),
    "blindspot_targeted": SystemSpec(
        name="blindspot_targeted",
        label="Blindspot (targeted search)",
        description=(
            "Identical to Blindspot except the adversary may read the implementation "
            "when choosing inputs. The obligation ledger it tests against still comes "
            "from the barrier-attested, spec-only Cartographer, and the Referee and "
            "Oracle still never see the code. Post-hoc; see PREREGISTRATION.md §8."
        ),
        kind="blindspot",
        overrides={"adversary_sees_impl": True},
    ),
    "agent_plus_oracle": SystemSpec(
        name="agent_plus_oracle",
        label="General agent + spec-anchored Oracle",
        description=(
            "The same ReAct agent, with every red test put in front of the Oracle: "
            "an independent reading of the specification that sees the call but not "
            "the test, the reasoning or the implementation. The Oracle can only "
            "remove a test, so detection can fall but cannot rise artificially."
        ),
        kind="agent_oracle",
        overrides={},
    ),
    "blindspot_search": SystemSpec(
        name="blindspot_search",
        label="Blindspot (search-first probes)",
        description=(
            "The pre-registered pipeline with one prompt change: the adversary is told "
            "to search the input domain with a property rather than pick a single input. "
            "It is given no extra information -- it still never sees the implementation "
            "body. Post-hoc; see PREREGISTRATION.md section 8."
        ),
        kind="blindspot",
        overrides={"prefer_search_probes": True},
    ),
    "abl_no_barrier": SystemSpec(
        name="abl_no_barrier",
        label="Ablation: roles without the barrier",
        description=(
            "Identical architecture, but the Cartographer's context includes impl.py. "
            "Isolates the information boundary from the mere existence of a separate role."
        ),
        kind="blindspot",
        overrides={"information_barrier": False},
    ),
    "abl_no_referee": SystemSpec(
        name="abl_no_referee",
        label="Ablation: no adjudication",
        description="Every red probe is reported without triage.",
        kind="blindspot",
        overrides={"referee": False},
    ),
    "abl_no_gate": SystemSpec(
        name="abl_no_gate",
        label="Ablation: no ambiguity gate",
        description="Obligations resting on unsettled ambiguities are probed and reported.",
        kind="blindspot",
        overrides={"ambiguity_gate": False},
    ),
    "abl_no_oracle": SystemSpec(
        name="abl_no_oracle",
        label="Ablation: no independent oracle",
        description=(
            "The referee's verdict stands unchecked. Measures how much of the "
            "false-alarm reduction comes from a second reading that never saw "
            "the accusation, as opposed to from adjudication itself."
        ),
        kind="blindspot",
        overrides={"oracle": False},
    ),
    "abl_clause_only_referee": SystemSpec(
        name="abl_clause_only_referee",
        label="Ablation: referee sees only the clause",
        description=(
            "Adjudication against the single clause the obligation came from, "
            "rather than the whole specification."
        ),
        kind="blindspot",
        overrides={"referee_full_spec": False},
    ),
    "abl_no_memory": SystemSpec(
        name="abl_no_memory",
        label="Ablation: no archetype memory",
        description="The adversary gets no prior failure patterns.",
        kind="blindspot",
        overrides={"memory": False},
    ),
    "abl_docstrings": SystemSpec(
        name="abl_docstrings",
        label="Ablation: leak the docstrings",
        description=(
            "The adversary's surface map includes the implementation's docstrings. "
            "Tests the finest-grained version of the thesis: is author prose enough "
            "to transmit the misreading, even without the code?"
        ),
        kind="blindspot",
        overrides={"surface_docstrings": True},
    ),
    "abl_no_property": SystemSpec(
        name="abl_no_property",
        label="Ablation: no property-based probes",
        description="Concrete examples only; Hypothesis is disallowed.",
        kind="blindspot",
        overrides={"property_probes": False},
    ),
}

DEFAULT_SYSTEMS = ["self_tests", "baseline_direct", "baseline_agent", "blindspot"]
ABLATIONS = [name for name in SYSTEMS if name.startswith("abl_")]


@dataclass
class RunRecord:
    system: str
    case_id: str
    report: AuditReport
    grade: CaseGrade
    trajectory: str


def _config_for(spec: SystemSpec, base: RunConfig) -> RunConfig:
    return replace(base, **spec.overrides)  # type: ignore[arg-type]


def _split_self_tests(source: str) -> list[str]:
    """Turn a multi-test suite into one self-contained module per test.

    The grader's contract is one verdict per emitted test, so a suite has to be
    split.  This is done with ``ast``, not by scanning for ``def test_``:

    * a decorated test (``@pytest.mark.parametrize``) must carry its decorators,
      or the parameter becomes a missing fixture and the test *errors* -- which
      would be silently miscounted as the suite being bad;
    * imports, module constants, fixtures and helper functions must be
      replicated into every produced module;
    * a test class is kept whole rather than dismembered.

    A textual split gets all three wrong.  The first version of this function
    was textual, and it manufactured four bogus "unsound" verdicts on the very
    first case it was run against; the regression tests in
    ``tests/test_splitting.py`` exist because of that.
    """
    if not source.strip():
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [source]

    lines = source.splitlines()

    def span(node: ast.AST) -> tuple[int, int]:
        decorators = [d.lineno for d in getattr(node, "decorator_list", [])]
        start = min([*decorators, node.lineno]) - 1  # type: ignore[attr-defined]
        return start, node.end_lineno  # type: ignore[attr-defined,return-value]

    spans: list[tuple[int, int]] = []
    for node in tree.body:
        is_test_fn = isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef
        ) and node.name.startswith("test_")
        is_test_cls = isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        if is_test_fn or is_test_cls:
            spans.append(span(node))

    if not spans:
        return [source]

    covered = {index for start, end in spans for index in range(start, end)}
    header = "\n".join(line for index, line in enumerate(lines) if index not in covered).rstrip()

    modules: list[str] = []
    for start, end in spans:
        body = "\n".join(lines[start:end]).rstrip()
        modules.append(f"{header}\n\n\n{body}\n" if header else f"{body}\n")
    return modules


def run_one(
    *,
    case: Case,
    spec: SystemSpec,
    base_config: RunConfig,
    store: CassetteStore,
    provider: BaseProvider | None,
    memory: ArchetypeMemory | None,
    trajectory_dir: Path,
    grade_repeats: int = 4,
) -> RunRecord:
    config = _config_for(spec, base_config)
    run_id = f"{spec.name}--{case.case_id}"
    trajectory_path = trajectory_dir / f"{run_id}.jsonl"
    recorder = TrajectoryRecorder(
        trajectory_path, run_id=run_id, case_id=case.case_id, system=spec.name
    )

    tests: list[str] = []
    error = ""

    if spec.kind == "self_tests":
        tests = _split_self_tests(case.self_tests_src)
        report = AuditReport(
            case_id=case.case_id,
            system=spec.name,
            verdict=Verdict.CLEAN,
            probes_run=len(tests),
            notes=["the implementing model's own suite, replayed verbatim"],
        )
        recorder.run_start(config={"system": spec.name}, inputs={"case_id": case.case_id})
        recorder.note(f"replaying {len(tests)} self-written test(s); no model call")
        recorder.run_end(verdict=report.verdict.value, findings=0, cost={})
    else:
        router = LLMRouter(config, recorder=recorder, store=store, provider=provider, scope=run_id)
        try:
            if spec.kind == "direct":
                result = run_direct(
                    case_id=case.case_id,
                    spec=case.spec,
                    impl_src=case.impl_src,
                    router=router,
                    recorder=recorder,
                    config=config,
                    system_name=spec.name,
                )
                report, tests = result.report, result.tests
            elif spec.kind in {"agent", "agent_oracle"}:
                result = run_agent(
                    case_id=case.case_id,
                    spec=case.spec,
                    impl_src=case.impl_src,
                    router=router,
                    recorder=recorder,
                    config=config,
                    system_name=spec.name,
                )
                report, tests = result.report, result.tests
                if spec.kind == "agent_oracle":
                    report, tests = adjudicate_tests(
                        case_id=case.case_id,
                        spec=case.spec,
                        impl_src=case.impl_src,
                        tests=tests,
                        config=config,
                        router=router,
                        recorder=recorder,
                        entrypoint=case.meta.entrypoint,
                        system_name=spec.name,
                        upstream=report,
                    )
            else:
                artefacts = audit(
                    case_id=case.case_id,
                    spec=case.spec,
                    impl_src=case.impl_src,
                    config=config,
                    router=router,
                    recorder=recorder,
                    memory=memory,
                    decisions=load_decisions(case.meta.task_id),
                    system_name=spec.name,
                    entrypoint=case.meta.entrypoint,
                )
                report = artefacts.report
                tests = report.emitted_tests()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            recorder.note(f"RUN FAILED: {error}\n{traceback.format_exc(limit=4)}")
            report = AuditReport(
                case_id=case.case_id,
                system=spec.name,
                verdict=Verdict.CLEAN,
                cost=router.cost,
                error=error,
            )

    grade = grade_case(
        case,
        system=spec.name,
        tests=tests,
        reported_verdict=report.verdict.value,
        timeout_s=base_config.sandbox_timeout_s + 5,
        repeats=grade_repeats,
        error=error,
    )
    return RunRecord(
        system=spec.name,
        case_id=case.case_id,
        report=report,
        grade=grade,
        trajectory=str(trajectory_path.name),
    )


def run_sweep(
    *,
    cases: list[Case],
    systems: list[str],
    config: RunConfig,
    memory: ArchetypeMemory | None = None,
    trajectory_dir: Path | None = None,
    grade_repeats: int = 4,
    progress: Callable[[str], None] | None = None,
    ablation_cases: list[Case] | None = None,
) -> list[RunRecord]:
    """Evaluate every (system, case) pair.

    ``ablation_cases`` lets the ablation configurations run on a subset while
    the headline systems run on the whole split.  Ablations answer "what does
    this component contribute", which is a *paired* question, so it is
    answerable on fewer cases; the headline comparison is not, and always uses
    everything.  The subset is fixed and recorded, and every ablation row is
    reported against full Blindspot **restricted to the same cases**, so the
    two columns are never quietly measuring different things.
    """
    store = CassetteStore(config.cassette_dir, strict=config.strict_replay)
    provider = build_provider(config)
    # The pools below nest (jobs x obligations), so the only honest place to
    # cap real parallelism is the router itself.
    set_inflight_limit(config.max_inflight or config.concurrency)
    trajectory_dir = trajectory_dir or config.trajectory_dir
    trajectory_dir.mkdir(parents=True, exist_ok=True)

    subset = {c.case_id for c in ablation_cases} if ablation_cases is not None else None
    jobs = [
        (case, SYSTEMS[name])
        for name in systems
        for case in cases
        if not (subset is not None and name.startswith("abl_") and case.case_id not in subset)
    ]
    records: list[RunRecord] = []

    def work(job: tuple[Case, SystemSpec]) -> RunRecord:
        case, spec = job
        record = run_one(
            case=case,
            spec=spec,
            base_config=config,
            store=store,
            provider=provider,
            memory=memory,
            trajectory_dir=trajectory_dir,
            grade_repeats=grade_repeats,
        )
        if progress:
            # Report against what the case actually is.  `detected` is only
            # ever aggregated over buggy cases, but on a clean one it can still
            # be true -- an over-specified test that the reference happens to
            # satisfy fails the candidate and passes the reference.  Checking
            # it first made those print as "detected", which reads like a win
            # and is in fact a false alarm.
            if record.grade.has_defect:
                outcome = "detected" if record.grade.detected else "missed"
            else:
                outcome = "FALSE ALARM" if record.grade.false_alarm else "clean"
            progress(f"{spec.name:>16} | {case.case_id:<28} | {outcome}")
        return record

    # Cassette replay is order-independent by construction (every prompt is
    # unique per stage and per repair attempt), so parallelism here cannot
    # change the result -- only the wall clock.
    workers = max(1, config.concurrency if config.provider != "replay" else config.concurrency * 2)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(work, jobs))

    if provider is not None:
        provider.close()
    return records


def save_records(records: list[RunRecord], path: Path, *, config: RunConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config_fingerprint": config.fingerprint(),
        "provider": config.provider,
        "models": {"fast": config.resolve("fast"), "smart": config.resolve("smart")},
        "records": [
            {
                "system": r.system,
                "case_id": r.case_id,
                "trajectory": r.trajectory,
                "grade": r.grade.to_dict(),
                "report": json.loads(r.report.model_dump_json()),
            }
            for r in sorted(records, key=lambda r: (r.system, r.case_id))
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_emitted_tests_are_runnable(
    records: list[RunRecord], cases: dict[str, Case]
) -> list[str]:
    """Sanity check used by the test suite: emitted tests must at least import."""
    problems: list[str] = []
    for record in records:
        case = cases[record.case_id]
        for finding in record.report.findings:
            result = run_probe(
                probe_code=finding.repro_test, impl_source=case.impl_src, timeout_s=20
            )
            if result.status.value == "error":
                problems.append(f"{record.system}/{record.case_id}/{finding.id}")
    return problems
