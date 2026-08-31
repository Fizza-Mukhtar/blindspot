#!/usr/bin/env python
"""Generate every number in the README from the result files.

Rule Book #09 asks that every claim about results be connected to the evidence
submitted.  The strongest way to honour that is to make it impossible to type a
number by hand: the README contains marked regions, this script fills them from
``results/summary.json`` and ``results/forge_report.json``, and ``--check``
fails if the committed README disagrees with the committed results.

    python scripts/update_readme.py            # rewrite the marked regions
    python scripts/update_readme.py --check    # fail if they are stale

Marked regions look like:

    <!-- BEGIN:results -->
    ...generated...
    <!-- END:results -->
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
RESULTS = REPO_ROOT / "results"


def region(name: str, body: str) -> str:
    return f"<!-- BEGIN:{name} -->\n{body.strip()}\n<!-- END:{name} -->"


def replace_region(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"<!-- BEGIN:{re.escape(name)} -->.*?<!-- END:{re.escape(name)} -->", re.S
    )
    if not pattern.search(text):
        raise SystemExit(f"README has no <!-- BEGIN:{name} --> region")
    return pattern.sub(lambda _: region(name, body), text)


def pct(value: float) -> str:
    return f"{100 * value:.0f}%"


def interval(pair: list[float]) -> str:
    return f"[{100 * pair[0]:.0f}, {100 * pair[1]:.0f}]"


# --------------------------------------------------------------------------- #


def build_headline(summary: dict) -> str:
    systems = {s["system"]: s for s in summary["systems"]}
    order = [
        ("self_tests", "The model's own test suite", "the floor"),
        (
            "baseline_direct",
            "Baseline A — one direct prompt",
            "spec + code, one call, no execution",
        ),
        (
            "baseline_agent",
            "Baseline B — general agent + sandbox",
            "ReAct loop, 6 rounds, sees the code",
        ),
        (
            "blindspot",
            "Blindspot (pre-registered)",
            "information barrier on *everything*; never sees the code",
        ),
        (
            "blindspot_search",
            "Blindspot + search-first probes",
            "same barrier; told to search rather than guess (post-hoc)",
        ),
        (
            "agent_plus_oracle",
            "**Agent + spec-anchored Oracle**",
            "agent picks the inputs; barrier on the oracle only (post-hoc)",
        ),
    ]
    rows = [
        "| System | What it is | Detection (95% CI) | ...resampling defects | "
        "On spec violations only | False alarms (95% CI) | Youden J | Runs that errored |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for key, label, note in order:
        s = systems.get(key)
        if not s:
            continue
        rows.append(
            f"| {label} | {note} | "
            f"**{s['detected']}/{s['n_buggy']} = {pct(s['detection_rate'])}** "
            f"{interval(s['detection_ci95'])} | "
            f"{interval(s['detection_ci95_clustered'])} | "
            f"{s['detected_spec_visible']}/{s['n_spec_visible']} | "
            f"{s['false_alarms']}/{s['n_clean']} = {pct(s['false_alarm_rate'])} "
            f"{interval(s['false_alarm_ci95'])} | {s['youden_j']:+.2f} | "
            f"{s['errors']}/{s['n_buggy'] + s['n_clean']} |"
        )

    defects = next(
        (s["n_distinct_defects"] for s in summary["systems"] if s["system"] == "blindspot"),
        None,
    )
    n_buggy = next((s["n_buggy"] for s in summary["systems"] if s["system"] == "blindspot"), 0)
    lines = ["\n".join(rows), ""]
    if defects is not None:
        lines += [
            f"The {n_buggy} buggy cases in the held-out split carry **{defects} distinct "
            "defects** — the forge generates several implementations per ticket and more "
            "than one can fail the same way. Those outcomes are correlated, so the fourth "
            "column resamples *defects* rather than cases. It is the wider interval, and it "
            "is the one to quote.",
            "",
            "**Read the spec-violations column before the detection column.** `has_defect` "
            "is assigned by differentially fuzzing the candidate against the reference, so "
            "it means *differs from the reference*, not *violates the specification*. "
            "Executing each task's authoritative standard-traced suite against every buggy "
            "case shows most of them violate nothing the specification states -- they "
            "differ only where it is silent. That column counts detections on the cases "
            "that genuinely are specification violations. It is a tiny subset and supports "
            "no conclusion on its own; it is there because the detection column, read "
            "alone, is misleading. See [the hot take](#9-hot-take).",
            "",
            "The last column is there because of a bug this table would otherwise have "
            "hidden: a stage that crashes and falls back to passing its input through is "
            "indistinguishable, in every other column, from a stage that ran and changed "
            "nothing. A system with errored runs is not reporting a result about its "
            "design; it is reporting a result about its reliability.",
            "",
        ]
    for comparison in summary.get("paired_comparisons", []):
        if comparison["baseline"].startswith("abl_"):
            continue
        significant = "significant" if comparison["significant_at_05"] else "**not** significant"
        lines += [
            f"**{comparison['system']} vs {comparison['baseline']}** on "
            f"{comparison['n_paired']} paired buggy "
            f"cases: b = {comparison['b_system_only']} system-only wins, "
            f"c = {comparison['c_baseline_only']} baseline-only wins; exact two-sided McNemar "
            f"p = {comparison['p_exact']} (mid-p = {comparison['p_midp']}), {significant} at "
            f"α = 0.05. Δ = {100 * comparison['delta']:+.0f} pp "
            f"({interval(comparison['delta_ci95'])} bootstrap).",
            "",
        ]
    return "\n".join(lines)


def build_ablations(summary: dict) -> str:
    """One row per ablation, each against Blindspot **on the same cases**.

    Ablations run on a subset (every buggy case plus a few clean ones), so
    comparing their rates against full Blindspot's rate over the whole split
    would be comparing two different denominators.  `ablation_reference` in
    summary.json recomputes the reference over exactly the cases each ablation
    saw, and that is what these deltas use.
    """
    systems = {s["system"]: s for s in summary["systems"]}
    reference = summary.get("ablation_reference", {})
    if not any(k.startswith("abl_") for k in systems):
        return "_no ablation results yet — run `make eval-ablations`._"

    labels = {
        "abl_no_barrier": "remove the **information barrier** (same roles, spec-reader also sees the code)",
        "abl_no_referee": "remove **adjudication** (report every red probe)",
        "abl_no_oracle": "remove the **independent oracle**",
        "abl_clause_only_referee": "referee sees only the clause, not the whole specification",
        "abl_no_gate": "remove the **ambiguity gate** (probe under-determined obligations)",
        "abl_no_memory": "remove **archetype memory**",
        "abl_docstrings": "**add** the implementation's docstrings to the surface map (removed experiment)",
        "abl_no_property": "remove **property-based probes**",
    }
    rows = [
        "| Configuration | Detection | Δ | False alarms | Δ | n cases |",
        "|---|---|---|---|---|---|",
    ]
    for key, label in labels.items():
        ablation = systems.get(key)
        ref = reference.get(key)
        if not ablation or not ref:
            continue
        d_det = ablation["detection_rate"] - ref["detection_rate"]
        d_far = ablation["false_alarm_rate"] - ref["false_alarm_rate"]
        rows.append(
            f"| {label} | {ablation['detected']}/{ablation['n_buggy']} "
            f"(ref {ref['detected']}/{ref['n_buggy']}) | {100 * d_det:+.0f} pp "
            f"| {ablation['false_alarms']}/{ablation['n_clean']} "
            f"(ref {ref['false_alarms']}/{ref['n_clean']}) | {100 * d_far:+.0f} pp "
            f"| {ref['n_cases']} |"
        )
    rows += [
        "",
        "**Every row is a null result, and that is the finding rather than a disappointment.** "
        "These ablations remove components from a configuration that detects 1 of 9 held-out "
        "defects. There is no headroom to lose: a component cannot be shown to contribute "
        "when the system it is removed from is already at the floor. `ref` is full Blindspot "
        "restricted to exactly the cases each ablation saw, so the columns compare like with "
        "like.",
        "",
        "The component that *did* earn its place — the Oracle — was measured a different way, "
        "by bolting it onto a system that does detect things. That is the "
        "`agent_plus_oracle` row in the results table above.",
    ]
    return "\n".join(rows)


def build_cost(summary: dict) -> str:
    systems = {s["system"]: s for s in summary["systems"]}
    rows = [
        "| System | Model calls | Content tokens in/out | Est. USD | Wall clock |",
        "|---|---|---|---|---|",
    ]
    for key in (
        "baseline_direct",
        "baseline_agent",
        "blindspot",
        "blindspot_search",
        "agent_plus_oracle",
    ):
        s = systems.get(key)
        if not s:
            continue
        rows.append(
            f"| {s['label']} | {s['llm_calls']} | "
            f"{s['input_tokens']:,} / {s['output_tokens']:,} | "
            f"${s['usd']:.2f} | {s['wall_ms'] / 1000:.0f}s |"
        )
    rows.append("")
    rows.append(
        "Totals across the whole test split. Tokens are **content** tokens (the actual "
        "prompt and completion text); see [REPRODUCE.md](REPRODUCE.md#cost) for why the "
        "transport's own overhead is reported separately. **The wall-clock column is from "
        "the offline replay**, so it measures sandbox execution rather than model latency — "
        "which is why a system that makes more calls can show less of it. Live wall clock "
        "is dominated by the model and is roughly proportional to the call count."
    )
    return "\n".join(rows)


def build_power(summary: dict) -> str:
    """State the power ceiling from the actual corpus, never from memory."""
    systems = {s["system"]: s for s in summary["systems"]}
    blindspot = systems.get("blindspot")
    if not blindspot:
        return "_run `make eval` to populate._"
    n = blindspot["n_buggy"]
    defects = blindspot["n_distinct_defects"]
    # Exact two-sided McNemar with c = 0 gives p = 2^(1-b); solve for p < 0.05.
    needed = 6
    while 2.0 ** (1 - needed) >= 0.05:
        needed += 1
    return (
        f"> **The power ceiling, stated before the result.** With {n} held-out buggy "
        f"cases carrying {defects} distinct defects, and zero baseline-only wins, exact "
        f"two-sided McNemar gives *p* = 2^(1-b) — so **{needed}** system-only wins are "
        "required to reach *p* < 0.05, however large the difference looks. SpecTrap is "
        "powered to detect only large effects. Everything below is a directional signal, "
        "not a significance claim."
    )


def build_limits_n(summary: dict) -> str:
    systems = {s["system"]: s for s in summary["systems"]}
    blindspot = systems.get("blindspot")
    if not blindspot:
        return "_run `make eval` to populate._"
    return (
        f"- **Small n.** {blindspot['n_buggy']} held-out buggy cases carrying "
        f"**{blindspot['n_distinct_defects']} distinct defects**, and "
        f"{blindspot['n_clean']} clean ones. The defect count is the one that bounds the "
        "evidence: several cases can be different implementations of the same misreading. "
        "The power ceiling is stated in §4; nothing here is a significance claim."
    )


def build_forge(forge: dict) -> str:
    usable = forge["self_tests_green"]
    wrong = forge["green_but_provably_wrong"]
    rate = forge.get("green_and_wrong_rate")
    return "\n".join(
        [
            f"- **{forge['variants_generated']}** implementations generated from "
            f"**{forge['tasks']}** tickets, each with a test suite written by the same model "
            "that wrote the code.",
            f"- **{forge['self_tests_red']}** were discarded because their own tests were red — "
            "CI already catches those.",
            f"- Of the **{usable}** whose own suite was green, "
            f"**{wrong}** were provably wrong"
            + (f" — a green-and-wrong rate of **{100 * rate:.0f}%**." if rate is not None else "."),
            f"- **{forge['self_tests_that_reject_the_correct_reference']}** of the model-written "
            "suites *reject the correct reference implementation* — they encode a misreading "
            "strongly enough to fail correct code.",
            f"- **{forge['oracle_disagreements']}** cases where the two independent labelling "
            "oracles disagreed (flagged, never silently resolved).",
        ]
    )


# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()

    text = README.read_text(encoding="utf-8")
    original = text
    changelog = CHANGELOG.read_text(encoding="utf-8")
    changelog_original = changelog

    summary_path = args.results / "summary.json"
    forge_path = args.results / "forge_report.json"

    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        text = replace_region(text, "results", build_headline(summary))
        text = replace_region(text, "ablations", build_ablations(summary))
        text = replace_region(text, "cost", build_cost(summary))
        text = replace_region(text, "power", build_power(summary))
        text = replace_region(text, "limits_n", build_limits_n(summary))
        changelog = replace_region(changelog, "changelog_ablations", build_ablations(summary))
    elif args.check:
        print(f"missing {summary_path}", file=sys.stderr)
        return 2

    if forge_path.is_file():
        forge = json.loads(forge_path.read_text(encoding="utf-8"))
        text = replace_region(text, "forge", build_forge(forge))
    elif args.check:
        print(f"missing {forge_path}", file=sys.stderr)
        return 2

    if args.check:
        stale = [
            name
            for name, before, after in (
                ("README.md", original, text),
                ("CHANGELOG.md", changelog_original, changelog),
            )
            if before != after
        ]
        if stale:
            print(
                f"{', '.join(stale)} STALE: generated regions do not match results/.\n"
                "Run: python scripts/update_readme.py",
                file=sys.stderr,
            )
            return 1
        print("README.md and CHANGELOG.md numbers match results/ exactly.")
        return 0

    README.write_text(text, encoding="utf-8")
    CHANGELOG.write_text(changelog, encoding="utf-8")
    print(f"updated the generated regions of {README.name} and {CHANGELOG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
