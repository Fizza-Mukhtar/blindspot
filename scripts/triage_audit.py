#!/usr/bin/env python
"""Audit the Referee against the grader, finding by finding.

No headline number depends on the Referee's triage *category* -- detection and
false-alarm rates are execution predicates, computed by running tests against
the candidate and the hidden reference.  But "the category is not load-bearing"
is a claim worth checking rather than trusting, so this script puts the two
labels side by side:

    referee label   the pipeline emitted this finding, i.e. it survived
                    adjudication and the independent Oracle
    grader label    the emitted test FAILS on the candidate and PASSES on the
                    hidden reference -- a sound counterexample -- or does not

A finding the Referee kept and the grader calls unsound is a false accusation
that reached the reader.  That count, per system, is the Referee's precision,
and it is the number the adjudication stages exist to move.

    python scripts/triage_audit.py [--records results/records.json]

Writes ``results/triage_audit.csv`` and prints a per-system summary.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, default=REPO_ROOT / "results" / "records.json")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "results" / "triage_audit.csv")
    args = parser.parse_args(argv)

    if not args.records.is_file():
        print(f"error: {args.records} not found. Run `make eval` first.")
        return 1

    payload = json.loads(args.records.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []

    for record in payload["records"]:
        report = record["report"]
        verdicts = {v["index"]: v for v in record["grade"].get("verdicts", [])}
        for index, finding in enumerate(report.get("findings", [])):
            verdict = verdicts.get(index, {})
            sound = bool(verdict.get("sound"))
            unsound = bool(verdict.get("unsound"))
            rows.append(
                {
                    "system": record["system"],
                    "case_id": record["case_id"],
                    "finding_id": finding["id"],
                    "obligation_id": finding["obligation_id"],
                    "referee_outcome": finding["triage"]["outcome"],
                    "on_candidate": verdict.get("on_candidate", ""),
                    "on_reference": verdict.get("on_reference", ""),
                    "grader_label": (
                        "sound" if sound else ("unsound" if unsound else "not_a_counterexample")
                    ),
                    "false_accusation": int(unsound),
                    "title": finding["title"],
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["system"])
        writer.writeheader()
        writer.writerows(rows)

    by_system: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_system[str(row["system"])].append(row)

    print(f"wrote {args.out} ({len(rows)} finding(s))\n")
    print(f"{'system':<26} {'emitted':>7} {'sound':>6} {'unsound':>8} {'precision':>10}")
    for system in sorted(by_system):
        group = by_system[system]
        sound = sum(1 for r in group if r["grader_label"] == "sound")
        unsound = sum(1 for r in group if r["grader_label"] == "unsound")
        precision = f"{sound / len(group):.0%}" if group else "n/a"
        print(f"{system:<26} {len(group):>7} {sound:>6} {unsound:>8} {precision:>10}")

    print(
        "\nprecision = sound counterexamples / findings shown to the reader.\n"
        "An unsound finding is a false accusation that survived adjudication."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
