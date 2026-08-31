"""Rendering the audit into something a person would actually put their name on.

Three surfaces, one report:

``AUDIT.md``          the full write-up: verdict, findings with a minimal
                      reproducing input and the clause each one violates, the
                      questions that need a human, and what was *not* covered.
``repro/test_*.py``   runnable pytest files.  The point of the tool is not a
                      document -- it is a regression test the reader drops into
                      their repository and keeps.
``--format pr``       a pull-request comment: short, specific, no filler, and it
                      never says "consider" or "you may want to".

The house style is deliberate.  Findings lead with the evidence, quote the
specification verbatim, and stop.  There is no summary paragraph restating the
findings, no severity theatre, and no praise for the parts that were fine.
"""

from __future__ import annotations

import re
from pathlib import Path

from .types import AuditReport, Finding, Verdict

_SLUG = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    return _SLUG.sub("_", text.lower()).strip("_")[:48] or "finding"


def _finding_block(finding: Finding, *, index: int) -> list[str]:
    return [
        f"### {index}. {finding.title}",
        "",
        "> " + finding.spec_quote.replace("\n", "\n> "),
        "",
        f"**Input** `{finding.minimal_input}`",
        "",
        f"**Specification requires** {finding.expected}",
        f"**Implementation produces** {finding.actual}",
        "",
        f"<sub>{finding.obligation_id} · {finding.strategy.value} probe · "
        f"severity {finding.severity.value}"
        + (f" · reduced in {finding.shrink_steps} step(s)" if finding.shrink_steps else "")
        + "</sub>",
        "",
        "<details><summary>Reproducing test</summary>",
        "",
        "```python",
        finding.repro_test.strip(),
        "```",
        "",
        "</details>",
        "",
    ]


def render_audit_markdown(report: AuditReport, *, subject: str = "impl.py") -> str:
    headline = {
        Verdict.DEFECT: f"**{len(report.findings)} confirmed defect"
        + ("s" if len(report.findings) != 1 else "")
        + f"** in `{subject}`.",
        Verdict.CLEAN: f"No defect found in `{subject}`.",
        Verdict.NEEDS_HUMAN: f"No defect confirmed in `{subject}`, but the specification "
        "leaves questions open.",
    }[report.verdict]

    lines = [
        f"# Audit — `{subject}`",
        "",
        headline,
        "",
        f"Checked {report.obligations_probed} of {report.obligations_total} obligations "
        f"derived from the specification; ran {report.probes_run} probe"
        + ("s" if report.probes_run != 1 else "")
        + f"; discarded {report.probes_discarded} that did not survive adjudication."
        + (
            f" Of those, {report.withdrawn_by_oracle} had been upheld and were then "
            "withdrawn by an independent reading of the specification that never saw "
            "the accusation."
            if report.withdrawn_by_oracle
            else ""
        ),
        "",
    ]

    if report.findings:
        lines += ["## Findings", ""]
        for index, finding in enumerate(report.findings, start=1):
            lines += _finding_block(finding, index=index)

    if report.open_questions:
        lines += [
            "## Questions for the specification's author",
            "",
            "These are not defects. The specification does not determine the answer, so the "
            "implementation cannot be wrong about them — but somebody should decide.",
            "",
        ]
        for question in report.open_questions:
            lines.append(f"- **{question.question}**")
            for option in question.options:
                lines.append(f"  - {option}")
            if question.why_it_matters:
                lines.append(f"  <sub>{question.why_it_matters}</sub>")
        lines.append("")

    if report.verdict is Verdict.CLEAN and not report.findings:
        lines += [
            "## What was checked",
            "",
            "Every obligation above was probed and none of the probes found a counterexample. "
            "That is evidence of absence only to the extent that the obligations are complete; "
            "the ledger is in the trajectory if you want to check what was missed.",
            "",
        ]

    if report.notes:
        lines += ["## Notes", "", *[f"- {note}" for note in report.notes], ""]

    cost = report.cost
    lines += [
        "---",
        "",
        f"<sub>{report.system} · {cost.calls} model call"
        + ("s" if cost.calls != 1 else "")
        + f" · {cost.input_tokens + cost.output_tokens} tokens · ${cost.usd:.4f} · "
        f"{cost.wall_ms / 1000:.1f}s · {cost.sandbox_runs} sandboxed executions</sub>",
        "",
    ]
    return "\n".join(lines)


def render_pr_comment(report: AuditReport, *, subject: str = "impl.py") -> str:
    if not report.findings:
        if report.open_questions:
            body = [
                f"No defect found in `{subject}`, but the spec leaves "
                f"{len(report.open_questions)} question(s) open:",
                "",
            ]
            body += [f"- {q.question}" for q in report.open_questions]
            return "\n".join(body) + "\n"
        return f"No defect found in `{subject}`.\n"

    lines = []
    for finding in report.findings:
        lines += [
            f"**{finding.title}**",
            "",
            f"> {finding.spec_quote}",
            "",
            f"`{finding.minimal_input}` → expected {finding.expected}, got {finding.actual}",
            "",
            "```python",
            finding.repro_test.strip(),
            "```",
            "",
        ]
    return "\n".join(lines)


def write_artefacts(report: AuditReport, out_dir: Path, *, subject: str = "impl.py") -> list[Path]:
    """Write AUDIT.md, the machine-readable report, and the runnable repro tests."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    audit_md = out_dir / "AUDIT.md"
    audit_md.write_text(render_audit_markdown(report, subject=subject), encoding="utf-8")
    written.append(audit_md)

    report_json = out_dir / "audit.json"
    report_json.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    written.append(report_json)

    # Clear the previous run's regression tests before writing this run's.
    # Leaving them behind meant a re-audit that withdrew a finding still had the
    # withdrawn test sitting on disk, which is precisely the wrong file to leave
    # in front of somebody.
    repro_dir = out_dir / "repro"
    if repro_dir.is_dir():
        for stale in repro_dir.glob("test_*.py"):
            stale.unlink()

    if report.findings:
        repro_dir.mkdir(exist_ok=True)
        for index, finding in enumerate(report.findings, start=1):
            path = repro_dir / f"test_{index:02d}_{_slug(finding.title)}.py"
            header = (
                f'"""Regression test for: {finding.title}\n\n'
                f"Specification:\n    {finding.spec_quote}\n\n"
                f"Found by Blindspot ({finding.obligation_id}, {finding.strategy.value} probe).\n"
                f'"""\n\n'
            )
            path.write_text(header + finding.repro_test.strip() + "\n", encoding="utf-8")
            written.append(path)
    return written
