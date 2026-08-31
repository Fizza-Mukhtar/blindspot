#!/usr/bin/env python
"""Separate "violates the specification" from "differs from the reference".

`has_defect` is assigned by differential fuzzing: the implementation and the
hand-written reference disagree on some input.  That is a weaker property than
it looks.  Two correct implementations can disagree wherever the specification
does not determine an answer, so a corpus built this way contains both real
defects and mere *differences*.

This script executes the task's authoritative `selftest.py` -- whose every
assertion traces to a named clause of the specification or the standard it
cites -- against each buggy implementation:

    selftest FAILS  -> the implementation violates a stated requirement
                       (`spec_visible: true`)
    selftest PASSES -> it satisfies everything the specification pins down and
                       differs from the reference only where the specification
                       is silent (`spec_visible: false`)

The distinction matters because a verifier that only accuses when the
specification determines the answer *should* stay silent on the second kind,
and a benchmark that credits detections there is rewarding reference-mimicry
rather than conformance.

    python scripts/label_spec_visible.py            # write the labels
    python scripts/label_spec_visible.py --check    # fail if any are stale
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CASES = REPO_ROOT / "spectrap" / "cases"
TASKS = REPO_ROOT / "spectrap" / "tasks"


def selftest_fails_on(case_dir: Path, task_id: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copy(case_dir / "impl.py", work / "impl.py")
        shutil.copy(TASKS / task_id / "selftest.py", work / "test_authoritative.py")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "test_authoritative.py", "--no-header"],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return proc.returncode != 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    stale: list[str] = []
    counts = {"visible": 0, "under_determined": 0, "clean": 0}

    for meta_path in sorted(CASES.glob("*/meta.yaml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if not meta.get("has_defect"):
            if meta.get("spec_visible") is not None:
                meta.pop("spec_visible", None)
                if not args.check:
                    meta_path.write_text(
                        yaml.safe_dump(meta, sort_keys=True, allow_unicode=True), encoding="utf-8"
                    )
            counts["clean"] += 1
            continue

        visible = selftest_fails_on(meta_path.parent, meta["task_id"])
        counts["visible" if visible else "under_determined"] += 1
        if meta.get("spec_visible") != visible:
            stale.append(
                f"{meta['case_id']}: recorded {meta.get('spec_visible')}, actual {visible}"
            )
            if not args.check:
                meta["spec_visible"] = visible
                meta_path.write_text(
                    yaml.safe_dump(meta, sort_keys=True, allow_unicode=True), encoding="utf-8"
                )

    total = counts["visible"] + counts["under_determined"]
    print(
        f"buggy cases: {total}   spec-visible: {counts['visible']}   "
        f"under-determined: {counts['under_determined']}   clean: {counts['clean']}"
    )
    if stale and args.check:
        print("\nlabels are stale:")
        for line in stale:
            print(f"  {line}")
        return 1
    if stale:
        print(f"updated {len(stale)} label(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
