#!/usr/bin/env python
"""The two-minute demo.  Offline, no API key, no setup beyond `make install`.

It tells the story in the order it actually happens:

    1. a ticket a person wrote
    2. code a model wrote from that ticket
    3. the test suite that same model wrote for that code -- and it is GREEN
    4. the differential oracle showing the code is nonetheless wrong
    5. Blindspot's audit, replayed from cassettes
    6. the counterexample it produces, executed twice in front of you:
       RED on the implementation, GREEN on the hidden reference

Step 6 is the whole argument. A test that is merely red proves nothing; a test
that is red on this code and green on a correct one is a proof of defect.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.rule import Rule  # noqa: E402
from rich.syntax import Syntax  # noqa: E402
from rich.table import Table  # noqa: E402

from blindspot.agents.memory import ArchetypeMemory  # noqa: E402
from blindspot.agents.pipeline import audit  # noqa: E402
from blindspot.config import RunConfig, load_dotenv  # noqa: E402
from blindspot.corpus import Case, load_cases  # noqa: E402
from blindspot.decisions import load_decisions  # noqa: E402
from blindspot.forge.fuzz import differential  # noqa: E402
from blindspot.llm.router import LLMRouter  # noqa: E402
from blindspot.render import render_audit_markdown  # noqa: E402
from blindspot.sandbox.runner import run_probe, run_suite  # noqa: E402
from blindspot.trace.recorder import TrajectoryRecorder  # noqa: E402
from blindspot.types import RunStatus  # noqa: E402

console = Console(width=100)


def beat(seconds: float) -> None:
    """A pause, so the demo is watchable rather than a wall of text."""
    time.sleep(seconds)


def pick_case(case_id: str | None) -> Case:
    cases = load_cases()
    if not cases:
        console.print("[red]No forged cases found. Run `blindspot forge` first.[/red]")
        raise SystemExit(1)
    if case_id:
        match = [c for c in cases if c.case_id == case_id]
        if not match:
            console.print(f"[red]No case {case_id!r}.[/red]")
            raise SystemExit(1)
        return match[0]
    buggy = [c for c in cases if c.meta.has_defect and c.meta.split == "test"]
    return (buggy or [c for c in cases if c.meta.has_defect] or cases)[0]


def spec_excerpt(spec: str, limit: int = 26) -> str:
    lines = spec.splitlines()
    head = lines[:limit]
    if len(lines) > limit:
        head.append(f"... ({len(lines) - limit} more lines)")
    return "\n".join(head)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default=None, help="case id (default: first buggy test case)")
    parser.add_argument("--provider", default="replay")
    parser.add_argument("--pace", type=float, default=1.0, help="0 for no pauses")
    args = parser.parse_args()

    load_dotenv()
    case = pick_case(args.case)
    pace = args.pace

    console.print()
    console.print(
        Panel(
            "[bold]AI writes the code. AI writes the tests.[/bold]\n"
            "Both are written from the same reading of the same specification —\n"
            "so when the reading is wrong, the tests agree with the bug and CI goes green.",
            title="Blindspot",
            border_style="cyan",
        )
    )
    beat(pace)

    # ---- 1. the ticket ---------------------------------------------------- #
    console.print(Rule(f"[bold]1.  The ticket[/bold]  ·  {case.task.title}"))
    console.print(Syntax(spec_excerpt(case.spec), "markdown", theme="ansi_dark", word_wrap=True))
    console.print(f"[dim]full ticket: spectrap/tasks/{case.meta.task_id}/SPEC.md[/dim]")
    beat(pace * 2)

    # ---- 2. the code a model wrote ---------------------------------------- #
    console.print(Rule("[bold]2.  What a model wrote from it[/bold]"))
    console.print(Syntax(case.impl_src[:1400], "python", theme="ansi_dark", line_numbers=False))
    console.print(f"[dim]spectrap/cases/{case.case_id}/impl.py[/dim]")
    beat(pace * 2)

    # ---- 3. its own tests are green --------------------------------------- #
    console.print(Rule("[bold]3.  The tests that same model wrote for that code[/bold]"))
    with console.status("running the model's own test suite..."):
        own = run_suite(suite_code=case.self_tests_src, impl_source=case.impl_src, timeout_s=120)
    summary = own.stdout.strip().splitlines()[-1] if own.stdout.strip() else own.status.value
    colour = "green" if own.status is RunStatus.PASS else "red"
    console.print(
        Panel(
            f"[{colour}]{summary}[/{colour}]",
            title="pytest — the model's own suite, on the model's own code",
            border_style=colour,
        )
    )
    console.print("[dim]This is what CI would show. A reviewer approves and it ships.[/dim]")
    beat(pace * 2)

    # ---- 4. but the code is wrong ----------------------------------------- #
    console.print(Rule("[bold]4.  It is nonetheless wrong[/bold]"))
    with console.status("differentially fuzzing against the hidden reference..."):
        fuzz = differential(
            reference_src=case.reference_src,
            candidate_src=case.impl_src,
            generators_src=case.task.generators_src,
            entrypoint=case.entrypoint,
            budget=2000,
        )
    if fuzz.witness:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[bold]input[/bold]", fuzz.witness.call_repr(case.entrypoint)[:150])
        table.add_row(
            "[bold]specification requires[/bold]", fuzz.witness.reference_outcome[1][:150]
        )
        table.add_row("[bold]this code returns[/bold]", fuzz.witness.candidate_outcome[1][:150])
        console.print(Panel(table, border_style="red", title="ground truth, found by execution"))
        console.print(
            f"[dim]{fuzz.checked} inputs compared. The label is assigned by this oracle, "
            "never by a model.[/dim]"
        )
    else:
        console.print("[green]No divergence found — this case is a clean control.[/green]")
    beat(pace * 2)

    # ---- 5. the audit ------------------------------------------------------ #
    console.print(Rule("[bold]5.  Blindspot audits it[/bold]"))
    console.print(
        "[dim]The spec-reading agent never sees impl.py. Obligations come from the ticket "
        "alone;\nonly then does an adversary try to falsify the code against them.[/dim]\n"
    )
    config = RunConfig(provider=args.provider, concurrency=6)
    recorder = TrajectoryRecorder(
        REPO_ROOT / "trajectories" / f"demo--{case.case_id}.jsonl",
        run_id=f"demo--{case.case_id}",
        case_id=case.case_id,
        system="blindspot",
    )
    router = LLMRouter(config, recorder=recorder)
    with console.status("auditing (replaying committed cassettes — no API key, no network)..."):
        artefacts = audit(
            case_id=case.case_id,
            spec=case.spec,
            impl_src=case.impl_src,
            config=config,
            router=router,
            recorder=recorder,
            memory=ArchetypeMemory.load(),
            decisions=load_decisions(case.meta.task_id),
        )
    router.close()
    report = artefacts.report

    if artefacts.attestation is not None:
        console.print(
            f"[green]barrier attested[/green]: 0 of {artefacts.attestation.impl_lines_checked} "
            "implementation lines appeared in the spec-reader's context "
            f"[dim](context sha256 {artefacts.attestation.context_sha256[:12]})[/dim]"
        )
    console.print(
        f"[dim]{report.obligations_total} obligations derived · "
        f"{report.obligations_probed} probed · {report.probes_run} probes executed · "
        f"{report.probes_discarded} discarded by adjudication[/dim]\n"
    )
    console.print(render_audit_markdown(report, subject=f"{case.case_id}/impl.py"))
    beat(pace * 2)

    # ---- 6. the proof ------------------------------------------------------ #
    if not report.findings:
        console.print(Rule("[bold]6.  No defect claimed[/bold]"))
        console.print("Blindspot reported no defect on this case.")
        return 0

    console.print(Rule("[bold]6.  The proof: same test, two implementations[/bold]"))
    finding = report.findings[0]
    console.print(Syntax(finding.repro_test.strip(), "python", theme="ansi_dark"))
    console.print()

    with console.status("executing the counterexample against both..."):
        on_impl = run_probe(probe_code=finding.repro_test, impl_source=case.impl_src, timeout_s=40)
        on_ref = run_probe(
            probe_code=finding.repro_test, impl_source=case.reference_src, timeout_s=40
        )

    verdict = Table(show_header=True, header_style="bold")
    verdict.add_column("target")
    verdict.add_column("result")
    verdict.add_column("meaning")
    verdict.add_row(
        "the model's implementation",
        f"[red]{on_impl.status.value.upper()}[/red]",
        "the code violates the quoted clause",
    )
    verdict.add_row(
        "the hidden reference",
        f"[green]{on_ref.status.value.upper()}[/green]",
        "the test is right about the specification",
    )
    console.print(verdict)

    sound = on_impl.status is RunStatus.FAIL and on_ref.status is RunStatus.PASS
    console.print()
    console.print(
        Panel(
            "[bold green]Sound counterexample.[/bold green]  Red on this code, green on a correct "
            "one.\nThat conjunction is the entire scoring rule — and it is why `assert False`,\n"
            "which is red on everything, scores zero."
            if sound
            else "[yellow]Not credited: a counterexample must fail here and pass on the "
            "reference.[/yellow]",
            border_style="green" if sound else "yellow",
        )
    )
    console.print(
        f"\n[dim]trajectory: {recorder.path.relative_to(REPO_ROOT)}  ·  "
        "render it with `make trace`[/dim]"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
