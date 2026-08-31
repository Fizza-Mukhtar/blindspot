#!/usr/bin/env python
"""Assert a replayed run reproduces the published one, exactly.

``make reproduce`` regenerates every result from committed cassettes and then
runs this.  It compares the **per-case outcome table**, not a summary: two runs
can agree on a headline percentage while disagreeing about which cases they got
right, and that would be a reproduction failure worth knowing about.

Exits non-zero, loudly, on any drift.  A reproduction step that can quietly
pass while the numbers moved is worse than no reproduction step.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Columns that must match exactly.  Cost and wall-clock are deliberately
# excluded: they are machine-dependent and are reported, not asserted.
OUTCOME_COLUMNS = [
    "detected",
    "detected_lenient",
    "false_alarm",
    "tests_emitted",
    "sound_counterexamples",
    "unsound_claims",
    "has_defect",
    "split",
]


def load_per_case(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {(row["system"], row["case_id"]): row for row in csv.DictReader(handle)}


def compare(expected_dir: Path, actual_dir: Path) -> int:
    expected_csv = expected_dir / "per_case.csv"
    actual_csv = actual_dir / "per_case.csv"
    for path in (expected_csv, actual_csv):
        if not path.is_file():
            print(f"MISSING: {path}", file=sys.stderr)
            return 2

    expected = load_per_case(expected_csv)
    actual = load_per_case(actual_csv)

    problems: list[str] = []

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    for key in missing:
        problems.append(f"missing run: {key[0]} / {key[1]}")
    for key in extra:
        problems.append(f"unexpected run: {key[0]} / {key[1]}")

    for key in sorted(set(expected) & set(actual)):
        for column in OUTCOME_COLUMNS:
            want, got = expected[key].get(column), actual[key].get(column)
            if want != got:
                problems.append(f"{key[0]} / {key[1]} / {column}: expected {want!r}, got {got!r}")

    # Headline metrics, cross-checked from summary.json as a second signal.
    try:
        want_summary = json.loads((expected_dir / "summary.json").read_text(encoding="utf-8"))
        got_summary = json.loads((actual_dir / "summary.json").read_text(encoding="utf-8"))

        def rates(summary: dict, label: str) -> dict[str, tuple]:
            systems = summary.get("systems")
            if not isinstance(systems, list) or not all(isinstance(s, dict) for s in systems):
                raise ValueError(
                    f"{label}/summary.json has an unrecognised `systems` shape "
                    "(expected a list of objects). It was probably written by an "
                    "older version -- regenerate it with `make eval`."
                )
            return {s["system"]: (s["detection_rate"], s["false_alarm_rate"]) for s in systems}

        want_rates = rates(want_summary, "expected")
        got_rates = rates(got_summary, "actual")
        for system in sorted(set(want_rates) | set(got_rates)):
            if want_rates.get(system) != got_rates.get(system):
                problems.append(
                    f"summary {system}: expected DR/FAR {want_rates.get(system)}, "
                    f"got {got_rates.get(system)}"
                )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        problems.append(f"could not compare summary.json: {exc}")

    total = len(set(expected) & set(actual))
    if problems:
        print(f"REPRODUCTION FAILED — {len(problems)} difference(s) across {total} runs:\n")
        for problem in problems[:40]:
            print(f"  - {problem}")
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
        print(
            "\nIf you changed a prompt or the pipeline, this is expected: re-record with "
            "`make record` and commit the new cassettes and results together."
        )
        return 1

    print(f"REPRODUCED — {total} runs matched exactly on {len(OUTCOME_COLUMNS)} outcome columns.")
    print(f"  expected: {expected_csv}")
    print(f"  actual:   {actual_csv}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("actual", type=Path)
    args = parser.parse_args()
    return compare(args.expected, args.actual)


if __name__ == "__main__":
    raise SystemExit(main())
