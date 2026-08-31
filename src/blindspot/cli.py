"""``blindspot`` command line interface.

blindspot doctor                     check the environment
blindspot corpus                     list tasks, cases and the split
blindspot audit --spec S --impl I    audit any (specification, code) pair
blindspot forge                      build SpecTrap from the task library
blindspot eval                       run the benchmark sweep and score it
blindspot decide TASK_ID             answer the questions a spec leaves open
blindspot learn                      build archetype memory from the dev split
blindspot trace                      render trajectories to a single HTML file
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from dataclasses import replace
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .agents.memory import ArchetypeMemory
from .agents.pipeline import audit as run_audit
from .config import (
    CASES_DIR,
    MEMORY_PATH,
    RESULTS_DIR,
    SPECTRAP_DIR,
    TRAJECTORY_DIR,
    RunConfig,
    config_from_env,
    load_dotenv,
)
from .corpus import Case, draw_split, load_cases, load_tasks, task_index
from .decisions import load_decisions, save_decision
from .llm.cassette import CassetteStore
from .llm.router import LLMRouter
from .render import render_audit_markdown, render_pr_comment, write_artefacts
from .trace.recorder import TrajectoryRecorder
from .types import sha256_text

# Windows consoles still default to a legacy code page, and the results table
# contains characters (alpha, delta, arrows) that cp1252 cannot encode.  Rich
# raises UnicodeEncodeError from inside its own writer, which crashed `eval`
# *after* it had written every result file -- a traceback where a summary
# should be.  Reconfiguring to UTF-8 with replacement makes output degrade to a
# placeholder glyph instead of killing the command.
for _stream in (sys.stdout, sys.stderr):
    with contextlib.suppress(AttributeError, ValueError, OSError):
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

console = Console()


# --------------------------------------------------------------------------- #


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        default=None,
        choices=["replay", "claude_cli", "anthropic", "openai", "mock"],
        help="model backend (default: BLINDSPOT_PROVIDER, or replay)",
    )
    parser.add_argument("--model-fast", default=None)
    parser.add_argument("--model-smart", default=None)
    parser.add_argument("--record", action="store_true", help="write cassettes while running live")
    parser.add_argument("--concurrency", type=int, default=None)
    parser.add_argument(
        "--inflight",
        type=int,
        default=None,
        help="hard ceiling on simultaneous model calls (default: --concurrency)",
    )
    parser.add_argument("--seed", type=int, default=None)


def _config(args: argparse.Namespace, **extra: object) -> RunConfig:
    load_dotenv()
    config = config_from_env()
    overrides: dict[str, object] = dict(extra)
    if args.provider:
        overrides["provider"] = args.provider
    if getattr(args, "model_fast", None):
        overrides["model_fast"] = args.model_fast
    if getattr(args, "model_smart", None):
        overrides["model_smart"] = args.model_smart
    if getattr(args, "record", False):
        overrides["record"] = True
    if getattr(args, "concurrency", None):
        overrides["concurrency"] = args.concurrency
    if getattr(args, "inflight", None):
        overrides["max_inflight"] = args.inflight
    if getattr(args, "seed", None):
        overrides["seed"] = args.seed
    return replace(config, **overrides)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #


def cmd_doctor(args: argparse.Namespace) -> int:
    import platform
    import shutil

    config = _config(args)
    table = Table(title="blindspot doctor", show_header=True, header_style="bold")
    table.add_column("check")
    table.add_column("result")

    table.add_row("python", f"{platform.python_version()} on {platform.system()}")
    table.add_row("provider", config.provider)
    table.add_row("models", f"fast={config.resolve('fast')}  smart={config.resolve('smart')}")
    table.add_row("config fingerprint", config.fingerprint())

    for module in ("pytest", "hypothesis", "pydantic", "yaml", "rich", "jinja2"):
        try:
            __import__(module)
            table.add_row(f"import {module}", "[green]ok[/green]")
        except ImportError:
            table.add_row(f"import {module}", "[red]MISSING[/red]")

    store = CassetteStore(config.cassette_dir)
    manifest = store.manifest()
    table.add_row(
        "cassettes",
        f"{manifest['recordings']} recording(s), "
        f"{manifest['input_tokens'] + manifest['output_tokens']} tokens",
    )
    table.add_row("tasks", str(len(load_tasks())))
    cases = load_cases()
    buggy = sum(1 for c in cases if c.meta.has_defect)
    table.add_row("cases", f"{len(cases)} ({buggy} buggy, {len(cases) - buggy} clean)")

    if config.provider == "claude_cli":
        from .llm.claude_cli import _discover_executable

        found = _discover_executable() or shutil.which("claude")
        table.add_row("claude CLI", found or "[red]not found[/red]")

    # A live smoke test only when a live provider is selected.
    if config.provider not in ("replay", "mock"):
        try:
            router = LLMRouter(replace(config, record=False))
            response = router.complete(
                purpose="doctor", system="Reply with exactly: PONG", user="ping", role="fast"
            )
            table.add_row("live call", f"[green]ok[/green] ({response.text.strip()[:20]})")
            router.close()
        except Exception as exc:
            table.add_row("live call", f"[red]{type(exc).__name__}: {str(exc)[:120]}[/red]")

    console.print(table)
    from .sandbox.runner import run_probe

    probe = run_probe(
        probe_code="def test_ok():\n    assert 1 + 1 == 2\n", impl_source="x = 1\n", timeout_s=60
    )
    console.print(
        f"sandbox: [{'green' if probe.status.value == 'pass' else 'red'}]{probe.status.value}[/]"
    )
    return 0


# --------------------------------------------------------------------------- #
# corpus
# --------------------------------------------------------------------------- #


def cmd_corpus(args: argparse.Namespace) -> int:
    tasks = load_tasks()
    split = _load_or_draw_split([t.task_id for t in tasks])

    table = Table(title=f"SpecTrap task library ({len(tasks)} tasks)", header_style="bold")
    for column in ("task", "split", "diff", "entrypoint", "trap class", "grounding"):
        table.add_column(column, overflow="fold")
    for task in tasks:
        table.add_row(
            task.task_id,
            split.get(task.task_id, "?"),
            str(task.difficulty),
            task.entrypoint,
            task.trap_class,
            task.grounding_standard or task.grounding_url,
        )
    console.print(table)

    cases = load_cases()
    if cases:
        case_table = Table(title=f"Forged cases ({len(cases)})", header_style="bold")
        for column in ("case", "split", "label", "witness"):
            case_table.add_column(column, overflow="fold")
        for case in cases:
            case_table.add_row(
                case.case_id,
                case.meta.split,
                "[red]buggy[/red]" if case.meta.has_defect else "[green]clean[/green]",
                (case.meta.witness_input or "-")[:70],
            )
        console.print(case_table)
    else:
        console.print("[yellow]No forged cases yet. Run `blindspot forge`.[/yellow]")
    return 0


def _load_or_draw_split(task_ids: list[str]) -> dict[str, str]:
    import yaml

    path = SPECTRAP_DIR / "SPLIT.yaml"
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return dict(raw.get("assignments", {}))
    return draw_split(task_ids)


def cmd_split(args: argparse.Namespace) -> int:
    """Draw and freeze the dev/test split.  Run once, before any evaluation."""
    import yaml

    tasks = load_tasks()
    task_ids = [t.task_id for t in tasks]
    assignments = draw_split(task_ids, seed=args.seed or 20260828, dev_size=args.dev_size)
    path = SPECTRAP_DIR / "SPLIT.yaml"
    if path.is_file() and not args.force:
        console.print(
            f"[red]{path} already exists.[/red] Re-drawing a frozen split invalidates "
            "every held-out number. Pass --force only if you know why."
        )
        return 1
    payload = {
        "drawn_by": "blindspot split",
        "seed": args.seed or 20260828,
        "dev_size": args.dev_size,
        "procedure": (
            "sorted(task_ids) shuffled with random.Random(seed); the first dev_size go to dev. "
            "Drawn once, before any system was run against the test split."
        ),
        "task_ids_sha256": sha256_text(",".join(sorted(task_ids))),
        "assignments": assignments,
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    console.print(f"wrote {path}")
    for task_id, which in sorted(assignments.items(), key=lambda kv: (kv[1], kv[0])):
        console.print(f"  {which:<5} {task_id}")
    return 0


# --------------------------------------------------------------------------- #
# audit
# --------------------------------------------------------------------------- #


def cmd_audit(args: argparse.Namespace) -> int:
    config = _config(args, max_obligations=args.max_obligations)
    spec_path, impl_path = Path(args.spec), Path(args.impl)
    spec = spec_path.read_text(encoding="utf-8")
    impl_src = impl_path.read_text(encoding="utf-8")

    out_dir = Path(args.out) if args.out else Path(".blindspot") / impl_path.stem
    run_id = f"audit--{impl_path.stem}"
    recorder = TrajectoryRecorder(
        (Path(args.trajectory_dir) if args.trajectory_dir else TRAJECTORY_DIR) / f"{run_id}.jsonl",
        run_id=run_id,
        case_id=impl_path.stem,
        system="blindspot",
    )
    router = LLMRouter(config, recorder=recorder)
    memory = ArchetypeMemory.load() if config.memory else None

    with console.status(f"auditing {impl_path.name} against {spec_path.name}..."):
        artefacts = run_audit(
            case_id=impl_path.stem,
            spec=spec,
            impl_src=impl_src,
            config=config,
            router=router,
            recorder=recorder,
            memory=memory,
            decisions=load_decisions(args.task or impl_path.stem),
        )
    router.close()

    report = artefacts.report
    if args.format == "json":
        print(report.model_dump_json(indent=2))
    elif args.format == "pr":
        print(render_pr_comment(report, subject=impl_path.name))
    else:
        console.print(render_audit_markdown(report, subject=impl_path.name))

    written = write_artefacts(report, out_dir, subject=impl_path.name)
    console.print(f"\n[dim]wrote {len(written)} file(s) to {out_dir}[/dim]")
    console.print(f"[dim]trajectory: {recorder.path}[/dim]")
    return 0 if report.verdict.value != "DEFECT" else 2


# --------------------------------------------------------------------------- #
# forge
# --------------------------------------------------------------------------- #


def cmd_forge(args: argparse.Namespace) -> int:
    from .forge.forge import forge_all, write_forge_report

    config = _config(args)
    if config.provider == "replay" and not args.allow_replay:
        console.print(
            "[red]Forging needs a live provider.[/red] The committed corpus in "
            "spectrap/cases/ is the frozen artefact; re-forging changes the benchmark. "
            "Use --provider claude_cli (or anthropic) with --record, or pass "
            "--allow-replay to rebuild from cassettes."
        )
        return 1

    tasks = load_tasks()
    if args.only:
        tasks = [t for t in tasks if t.task_id in set(args.only)]
    split_map = _load_or_draw_split([t.task_id for t in load_tasks()])

    recorder = TrajectoryRecorder(
        TRAJECTORY_DIR / "forge.jsonl", run_id="forge", case_id="-", system="forge"
    )
    router = LLMRouter(config, recorder=recorder)
    report = forge_all(
        config,
        router=router,
        tasks=tasks,
        variants=args.variants,
        clean_target=args.clean_per_task,
        buggy_target=args.buggy_per_task,
        out_dir=Path(args.out) if args.out else CASES_DIR,
        split_map=split_map,
        impl_role=args.impl_model,
        variant_offset=args.variant_offset,
        spec_variant=args.spec_variant,
    )
    router.close()

    # Each pass writes its own report.  A single shared filename meant the
    # fourth pass silently overwrote the third's numbers -- the ones the corpus
    # documentation quotes -- so passes are addressed by label and the
    # aggregate is rebuilt from them.
    label = args.label or f"{args.spec_variant}-{args.impl_model}-{args.variant_offset:02d}"
    path = write_forge_report(report, RESULTS_DIR / "forge" / f"{label}.json")
    summary = report.to_dict()

    table = Table(title="Forge", header_style="bold")
    table.add_column("statistic")
    table.add_column("value", justify="right")
    table.add_row("tasks", str(summary["tasks"]))
    table.add_row("implementations generated", str(summary["variants_generated"]))
    table.add_row("self-written suites green", str(summary["self_tests_green"]))
    table.add_row("self-written suites red (discarded)", str(summary["self_tests_red"]))
    table.add_row("[bold]green but provably wrong[/bold]", str(summary["green_but_provably_wrong"]))
    table.add_row("green and equivalent to reference", str(summary["green_and_equivalent"]))
    rate = summary["green_and_wrong_rate"]
    table.add_row(
        "[bold]green-and-wrong rate[/bold]", f"{100 * rate:.0f}%" if rate is not None else "n/a"
    )
    table.add_row(
        "suites that reject the correct reference",
        str(summary["self_tests_that_reject_the_correct_reference"]),
    )
    table.add_row("oracle disagreements (flagged)", str(summary["oracle_disagreements"]))
    console.print(table)
    console.print(f"[dim]wrote {path}[/dim]")
    return 0


# --------------------------------------------------------------------------- #
# eval
# --------------------------------------------------------------------------- #


def cmd_eval(args: argparse.Namespace) -> int:
    from .eval.report import render_markdown, write_per_case_csv, write_summary_json
    from .eval.runner import ABLATIONS, DEFAULT_SYSTEMS, SYSTEMS, run_sweep, save_records

    config = _config(args, max_obligations=args.max_obligations)
    cases = load_cases(split=args.split, only=args.only)
    if not cases:
        console.print("[red]no cases found[/red] — run `blindspot forge` first.")
        return 1

    systems = list(args.systems) if args.systems else list(DEFAULT_SYSTEMS)
    if args.ablations:
        systems += [name for name in ABLATIONS if name not in systems]
    unknown = [name for name in systems if name not in SYSTEMS]
    if unknown:
        console.print(f"[red]unknown system(s): {unknown}[/red]")
        return 1

    # Ablations answer a paired question and may run on a subset; the headline
    # systems always run on the whole split.  The subset is "every buggy case,
    # plus the first N clean ones by case id" -- deterministic, and recorded in
    # the summary so the reader can see exactly what was covered.
    ablation_cases: list[Case] | None = None
    if args.ablation_clean is not None and args.ablation_clean >= 0:
        buggy = [c for c in cases if c.meta.has_defect]
        clean = sorted((c for c in cases if not c.meta.has_defect), key=lambda c: c.case_id)
        ablation_cases = buggy + clean[: args.ablation_clean]

    memory = ArchetypeMemory.load()
    console.print(
        f"[bold]{len(systems)} system(s) x {len(cases)} case(s)[/bold] "
        f"= {len(systems) * len(cases)} runs · provider={config.provider} · "
        f"fingerprint={config.fingerprint()}"
    )

    records = run_sweep(
        cases=cases,
        systems=systems,
        config=config,
        memory=memory,
        grade_repeats=args.grade_repeats,
        progress=lambda line: console.print(f"[dim]{line}[/dim]"),
        ablation_cases=ablation_cases,
    )

    out = Path(args.out) if args.out else RESULTS_DIR
    save_records(records, out / "records.json", config=config)
    write_per_case_csv(records, {c.case_id: c for c in cases}, out / "per_case.csv")
    comparisons = [
        (system, baseline)
        # Every configuration that makes a claim gets compared against both
        # baselines, not just the pre-registered one -- otherwise the headline
        # result would be the only comparison the report cannot check.
        for system in ("blindspot", "blindspot_search", "agent_plus_oracle")
        for baseline in ("baseline_direct", "baseline_agent")
        if system in systems and baseline in systems
    ]
    comparisons += [("blindspot", name) for name in systems if name.startswith("abl_")]
    payload = write_summary_json(
        records,
        out / "summary.json",
        split=args.split,
        comparisons=comparisons,
        extra={
            "config_fingerprint": config.fingerprint(),
            "models": {"fast": config.resolve("fast"), "smart": config.resolve("smart")},
            "n_cases": len(cases),
            "systems_evaluated": systems,
            "ablation_case_ids": (
                sorted(c.case_id for c in ablation_cases) if ablation_cases is not None else None
            ),
        },
    )
    markdown = render_markdown(payload)
    (out / "RESULTS.md").write_text(markdown, encoding="utf-8")
    console.print()
    console.print(markdown)
    console.print(
        f"[dim]wrote {out / 'per_case.csv'}, {out / 'summary.json'}, {out / 'RESULTS.md'}[/dim]"
    )
    return 0


# --------------------------------------------------------------------------- #
# decide  (the human checkpoint)
# --------------------------------------------------------------------------- #


def cmd_decide(args: argparse.Namespace) -> int:
    tasks = task_index()
    task = tasks.get(args.task)
    if task is None:
        console.print(f"[red]unknown task {args.task}[/red]")
        return 1

    existing = load_decisions(task.task_id)
    console.print(f"[bold]{task.title}[/bold]  ({task.task_id})")
    console.print(f"[dim]{len(existing)} question(s) already decided[/dim]\n")

    from .decisions import question_key

    answered = 0
    for question in task.open_questions:
        key = question_key(question)
        if key in existing and not args.redo:
            console.print(f"[green]already decided[/green] {question}")
            console.print(f"  -> {existing[key]}\n")
            continue
        console.print(f"[bold yellow]?[/bold yellow] {question}")
        console.print("[dim]Type your decision, or press Enter to leave it open.[/dim]")
        try:
            answer = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]stopped[/dim]")
            break
        if not answer:
            console.print(
                "[dim]left open — obligations resting on it will not be reported as defects[/dim]\n"
            )
            continue
        save_decision(
            task.task_id,
            question=question,
            resolution=answer,
            options=[],
            decided_by=args.by,
        )
        answered += 1
        console.print("[green]recorded[/green]\n")

    console.print(f"{answered} decision(s) written to decisions/{task.task_id}.yaml")
    return 0


# --------------------------------------------------------------------------- #
# learn / trace
# --------------------------------------------------------------------------- #


def cmd_learn(args: argparse.Namespace) -> int:
    from .agents.learn import learn_archetypes

    config = _config(args)
    split = _load_or_draw_split([t.task_id for t in load_tasks()])
    dev_tasks = [t for t in load_tasks() if split.get(t.task_id) == "dev"]
    if not dev_tasks:
        console.print("[red]no dev-split tasks found[/red]")
        return 1
    console.print(
        f"learning from {len(dev_tasks)} dev task(s): {', '.join(t.task_id for t in dev_tasks)}"
    )

    recorder = TrajectoryRecorder(
        TRAJECTORY_DIR / "learn.jsonl", run_id="learn", case_id="-", system="learn"
    )
    router = LLMRouter(config, recorder=recorder)
    memory = learn_archetypes(dev_tasks, router=router, recorder=recorder)
    router.close()
    path = memory.save(MEMORY_PATH)

    test_ids = [t.task_id for t in load_tasks() if split.get(t.task_id) == "test"]
    leaks = memory.leakage_report(test_ids)
    console.print(f"wrote {len(memory.archetypes)} archetype(s) to {path}")
    if leaks:
        console.print(f"[red]LEAKAGE: archetypes mention test-split task ids: {leaks}[/red]")
        return 1
    console.print("[green]no test-split leakage detected[/green]")
    return 0


def cmd_trace(args: argparse.Namespace) -> int:
    from .trace.render import render_index

    source = Path(args.dir) if args.dir else TRAJECTORY_DIR
    out = Path(args.out) if args.out else source / "viewer.html"
    files = sorted(source.glob("*.jsonl"))
    if args.only:
        files = [f for f in files if any(token in f.name for token in args.only)]
    if not files:
        console.print(f"[red]no .jsonl trajectories in {source}[/red]")
        return 1
    path = render_index(files, out, max_bytes=args.max_bytes)
    console.print(
        f"wrote {path} ({path.stat().st_size // 1024} KB, {len(files)} trajectory file(s))"
    )
    return 0


def cmd_cassettes(args: argparse.Namespace) -> int:
    config = _config(args)
    store = CassetteStore(config.cassette_dir)
    path = store.write_manifest()
    console.print(json.dumps(store.manifest(), indent=2))
    console.print(f"[dim]wrote {path}[/dim]")
    return 0


# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blindspot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="check the environment")
    _add_common(p)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("corpus", help="list tasks and forged cases")
    _add_common(p)
    p.set_defaults(func=cmd_corpus)

    p = sub.add_parser("split", help="draw and freeze the dev/test split")
    _add_common(p)
    p.add_argument("--dev-size", type=int, default=4)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("audit", help="audit a (specification, implementation) pair")
    _add_common(p)
    p.add_argument("--spec", required=True)
    p.add_argument("--impl", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--task", default=None, help="task id for the decisions file")
    p.add_argument("--trajectory-dir", default=None)
    p.add_argument("--max-obligations", type=int, default=10)
    p.add_argument("--format", choices=["markdown", "json", "pr"], default="markdown")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("forge", help="build SpecTrap cases from the task library")
    _add_common(p)
    p.add_argument("--variants", type=int, default=3)
    p.add_argument("--clean-per-task", type=int, default=2)
    p.add_argument("--buggy-per-task", type=int, default=1)
    p.add_argument(
        "--impl-model",
        choices=["fast", "smart"],
        default="smart",
        help="which model writes the implementation AND its own tests",
    )
    p.add_argument("--variant-offset", type=int, default=0)
    p.add_argument(
        "--label",
        default=None,
        help="name for this pass's report under results/forge/ (default: derived)",
    )
    p.add_argument(
        "--spec-variant",
        choices=["detailed", "terse"],
        default="detailed",
        help="which ticket rendition the implementer (and later the auditor) sees",
    )
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--allow-replay", action="store_true")
    p.set_defaults(func=cmd_forge)

    p = sub.add_parser("eval", help="run the benchmark sweep")
    _add_common(p)
    p.add_argument("--split", choices=["dev", "test"], default=None)
    p.add_argument("--systems", nargs="*", default=None)
    p.add_argument("--ablations", action="store_true")
    p.add_argument(
        "--ablation-clean",
        type=int,
        default=None,
        help=(
            "run ablation configurations on every buggy case plus this many clean "
            "cases, instead of the whole split (default: the whole split)"
        ),
    )
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--max-obligations", type=int, default=10)
    p.add_argument("--grade-repeats", type=int, default=4)
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("decide", help="answer the questions a specification leaves open")
    p.add_argument("task")
    p.add_argument("--by", default="human")
    p.add_argument("--redo", action="store_true")
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("learn", help="build archetype memory from the dev split")
    _add_common(p)
    p.set_defaults(func=cmd_learn)

    p = sub.add_parser("trace", help="render trajectories to a single HTML file")
    p.add_argument("--dir", default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--only", nargs="*", default=None)
    p.add_argument("--max-bytes", type=int, default=12_000_000)
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("cassettes", help="show the cassette manifest")
    _add_common(p)
    p.set_defaults(func=cmd_cassettes)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        console.print("\n[dim]interrupted[/dim]")
        return 130
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
