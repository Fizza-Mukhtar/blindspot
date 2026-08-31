"""Turn graded records into the artefacts a human reads.

Three outputs, all generated -- never hand-typed:

``results/per_case.csv``   one row per (system, case).  Every number in the
                           README can be recomputed from this file alone.
``results/summary.json``   the headline metrics with intervals and tests.
``results/RESULTS.md``     the table that goes in the README, generated.

The rule the project holds itself to is that no figure appears in prose unless
it can be traced to ``per_case.csv``.  ``scripts/check_readme_numbers.py``
enforces it.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from ..corpus import Case
from .runner import SYSTEMS, RunRecord
from .stats import (
    ClusteredRate,
    Proportion,
    cluster_bootstrap,
    mcnemar_exact,
    mcnemar_power_ceiling,
    paired_bootstrap,
    wilson,
)


@dataclass
class SystemSummary:
    system: str
    label: str
    detection: Proportion
    detection_spec_visible: Proportion
    detection_clustered: ClusteredRate
    detection_lenient: Proportion
    false_alarm: Proportion
    youden_j: float
    unsound_claims: int
    flakes: int
    tests_emitted: int
    calls: int
    input_tokens: int
    output_tokens: int
    usd: float
    wall_ms: int
    errors: int

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "label": self.label,
            "detection_rate": round(self.detection.value, 4),
            "detection_ci95": [round(self.detection.lo, 4), round(self.detection.hi, 4)],
            "detected": self.detection.successes,
            "n_buggy": self.detection.n,
            "detected_spec_visible": self.detection_spec_visible.successes,
            "n_spec_visible": self.detection_spec_visible.n,
            "detection_rate_spec_visible": round(self.detection_spec_visible.value, 4),
            "n_distinct_defects": self.detection_clustered.n_clusters,
            "detection_ci95_clustered": [
                round(self.detection_clustered.lo, 4),
                round(self.detection_clustered.hi, 4),
            ],
            "detection_rate_lenient": round(self.detection_lenient.value, 4),
            "false_alarm_rate": round(self.false_alarm.value, 4),
            "false_alarm_ci95": [round(self.false_alarm.lo, 4), round(self.false_alarm.hi, 4)],
            "false_alarms": self.false_alarm.successes,
            "n_clean": self.false_alarm.n,
            "youden_j": round(self.youden_j, 4),
            "unsound_claims": self.unsound_claims,
            "flakes": self.flakes,
            "tests_emitted": self.tests_emitted,
            "llm_calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "usd": round(self.usd, 4),
            "wall_ms": self.wall_ms,
            "errors": self.errors,
        }


def summarise(records: list[RunRecord], *, split: str | None = None) -> list[SystemSummary]:
    by_system: dict[str, list[RunRecord]] = {}
    for record in records:
        if split and record.grade.split != split:
            continue
        by_system.setdefault(record.system, []).append(record)

    summaries: list[SystemSummary] = []
    for system, rows in by_system.items():
        buggy = [r for r in rows if r.grade.has_defect]
        clean = [r for r in rows if not r.grade.has_defect]
        detection = wilson(sum(1 for r in buggy if r.grade.detected), len(buggy))
        visible = [r for r in buggy if r.grade.spec_visible]
        detection_visible = wilson(sum(1 for r in visible if r.grade.detected), len(visible))
        clustered = cluster_bootstrap(
            [r.grade.detected for r in buggy],
            [r.grade.trap_id or r.case_id for r in buggy],
        )
        lenient = wilson(sum(1 for r in buggy if r.grade.detected_lenient), len(buggy))
        far = wilson(sum(1 for r in clean if r.grade.false_alarm), len(clean))
        summaries.append(
            SystemSummary(
                system=system,
                label=SYSTEMS[system].label if system in SYSTEMS else system,
                detection=detection,
                detection_spec_visible=detection_visible,
                detection_clustered=clustered,
                detection_lenient=lenient,
                false_alarm=far,
                youden_j=detection.value - far.value,
                unsound_claims=sum(r.grade.unsound_claims for r in rows),
                flakes=sum(r.grade.flakes for r in rows),
                tests_emitted=sum(r.grade.emitted for r in rows),
                calls=sum(r.report.cost.calls for r in rows),
                input_tokens=sum(r.report.cost.input_tokens for r in rows),
                output_tokens=sum(r.report.cost.output_tokens for r in rows),
                usd=sum(r.report.cost.usd for r in rows),
                wall_ms=sum(r.report.cost.wall_ms for r in rows),
                errors=sum(1 for r in rows if r.grade.error),
            )
        )
    order = list(SYSTEMS)
    summaries.sort(key=lambda s: order.index(s.system) if s.system in order else 99)
    return summaries


def paired_comparison(
    records: list[RunRecord], *, system: str, baseline: str, split: str | None = None
) -> dict:
    """Exact McNemar plus a bootstrap interval, on the buggy cases only."""

    def outcomes(name: str) -> dict[str, bool]:
        return {
            r.case_id: r.grade.detected
            for r in records
            if r.system == name and r.grade.has_defect and (not split or r.grade.split == split)
        }

    a, b = outcomes(system), outcomes(baseline)
    shared = sorted(set(a) & set(b))
    left = [a[c] for c in shared]
    right = [b[c] for c in shared]
    test = mcnemar_exact(left, right)
    boot = paired_bootstrap(left, right, iterations=10_000)
    return {
        "system": system,
        "baseline": baseline,
        "n_paired": len(shared),
        "b_system_only": test.b,
        "c_baseline_only": test.c,
        "p_exact": round(test.p_exact, 5),
        "p_midp": round(test.p_midp, 5),
        "significant_at_05": test.significant,
        "power_note": mcnemar_power_ceiling(test.b, test.c),
        "delta": round(boot.delta, 4),
        "delta_ci95": [round(boot.lo, 4), round(boot.hi, 4)],
        "cases_system_only": [c for c in shared if a[c] and not b[c]],
        "cases_baseline_only": [c for c in shared if b[c] and not a[c]],
    }


def write_per_case_csv(records: list[RunRecord], cases: dict[str, Case], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "system",
                "case_id",
                "task_id",
                "split",
                "has_defect",
                "trap_id",
                "spec_visible",
                "trap_class",
                "detected",
                "detected_lenient",
                "false_alarm",
                "tests_emitted",
                "sound_counterexamples",
                "unsound_claims",
                "flakes",
                "reported_verdict",
                "llm_calls",
                "input_tokens",
                "output_tokens",
                "usd",
                "wall_ms",
                "error",
            ]
        )
        for record in sorted(records, key=lambda r: (r.system, r.case_id)):
            grade = record.grade
            case = cases.get(record.case_id)
            writer.writerow(
                [
                    record.system,
                    grade.case_id,
                    grade.task_id,
                    grade.split,
                    int(grade.has_defect),
                    grade.trap_id,
                    "" if grade.spec_visible is None else int(grade.spec_visible),
                    case.meta.trap_class if case else "",
                    int(grade.detected),
                    int(grade.detected_lenient),
                    int(grade.false_alarm),
                    grade.emitted,
                    grade.sound_counterexamples,
                    grade.unsound_claims,
                    grade.flakes,
                    grade.reported_verdict,
                    record.report.cost.calls,
                    record.report.cost.input_tokens,
                    record.report.cost.output_tokens,
                    f"{record.report.cost.usd:.6f}",
                    record.report.cost.wall_ms,
                    grade.error,
                ]
            )
    return path


def _restricted(records: list[RunRecord], *, reference: str, other: str, split: str | None) -> dict:
    """Summarise ``reference`` over only the cases ``other`` was run on."""
    shared = {
        r.case_id for r in records if r.system == other and (not split or r.grade.split == split)
    }
    rows = [
        r
        for r in records
        if r.system == reference and r.case_id in shared and (not split or r.grade.split == split)
    ]
    buggy = [r for r in rows if r.grade.has_defect]
    clean = [r for r in rows if not r.grade.has_defect]
    detection = wilson(sum(1 for r in buggy if r.grade.detected), len(buggy))
    far = wilson(sum(1 for r in clean if r.grade.false_alarm), len(clean))
    return {
        "n_cases": len(rows),
        "detected": detection.successes,
        "n_buggy": detection.n,
        "detection_rate": round(detection.value, 4),
        "false_alarms": far.successes,
        "n_clean": far.n,
        "false_alarm_rate": round(far.value, 4),
    }


def write_summary_json(
    records: list[RunRecord],
    path: Path,
    *,
    split: str | None,
    comparisons: list[tuple[str, str]],
    extra: dict | None = None,
) -> dict:
    summaries = summarise(records, split=split)
    payload = {
        "split": split or "all",
        "systems": [s.to_dict() for s in summaries],
        "paired_comparisons": [
            paired_comparison(records, system=s, baseline=b, split=split) for s, b in comparisons
        ],
        # An ablation may have been evaluated on fewer cases than the headline
        # run.  Comparing its rate against full Blindspot's rate over the whole
        # split would be comparing two different denominators, so the reference
        # is recomputed over exactly the cases the ablation saw.
        "ablation_reference": {
            name: _restricted(records, reference="blindspot", other=name, split=split)
            for name in {r.system for r in records}
            if name.startswith("abl_")
        },
        **(extra or {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def render_markdown(payload: dict) -> str:
    lines = [
        f"# SpecTrap results — `{payload['split']}` split",
        "",
        "Generated by `blindspot eval`. Every figure here is recomputed from",
        "`results/per_case.csv`; nothing in this file is hand-written.",
        "",
        "## Detection and false alarms",
        "",
        "| System | Detection rate (95% CI) | ...clustered by defect | False-alarm rate (95% CI) | Youden J | Unsound claims | Tests emitted | Calls | USD |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for system in payload["systems"]:
        detection = (
            f"{system['detected']}/{system['n_buggy']} = {100 * system['detection_rate']:.0f}% "
            f"[{100 * system['detection_ci95'][0]:.0f}, {100 * system['detection_ci95'][1]:.0f}]"
        )
        clustered = (
            f"[{100 * system['detection_ci95_clustered'][0]:.0f}, "
            f"{100 * system['detection_ci95_clustered'][1]:.0f}] "
            f"({system['n_distinct_defects']} defect(s))"
        )
        far = (
            f"{system['false_alarms']}/{system['n_clean']} = {100 * system['false_alarm_rate']:.0f}% "
            f"[{100 * system['false_alarm_ci95'][0]:.0f}, {100 * system['false_alarm_ci95'][1]:.0f}]"
        )
        lines.append(
            f"| {system['label']} | {detection} | {clustered} | {far} | "
            f"{system['youden_j']:+.2f} | "
            f"{system['unsound_claims']} | {system['tests_emitted']} | {system['llm_calls']} | "
            f"${system['usd']:.3f} |"
        )

    lines += [
        "",
        "The corpus contains several independently generated implementations that carry",
        "the *same* defect, so their outcomes are correlated. The clustered interval",
        "resamples distinct defects rather than cases, and is the honest one to quote.",
        "",
        "## Paired comparisons (buggy cases only)",
        "",
    ]
    for comparison in payload["paired_comparisons"]:
        lines += [
            f"**{comparison['system']} vs {comparison['baseline']}** "
            f"(n = {comparison['n_paired']} paired cases)",
            "",
            f"- discordance: b = {comparison['b_system_only']} system-only, "
            f"c = {comparison['c_baseline_only']} baseline-only",
            f"- exact two-sided McNemar p = {comparison['p_exact']} "
            f"(mid-p = {comparison['p_midp']}) — "
            f"{'significant' if comparison['significant_at_05'] else 'NOT significant'} at α = 0.05",
            f"- Δ = {100 * comparison['delta']:+.1f} pp, 95% bootstrap "
            f"[{100 * comparison['delta_ci95'][0]:+.1f}, {100 * comparison['delta_ci95'][1]:+.1f}]",
            f"- {comparison['power_note']}",
            "",
        ]
    return "\n".join(lines) + "\n"
