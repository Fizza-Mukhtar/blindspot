#!/usr/bin/env python
"""Content-hash the benchmark so "frozen before the run" is checkable.

A pre-registration is only worth reading if the thing it registers cannot be
edited afterwards without trace.  This writes ``spectrap/CORPUS.lock``: a
sha256 per file for every task and case, plus one aggregate digest over all of
them, plus the split assignment.

    python scripts/freeze_corpus.py            # write the lock
    python scripts/freeze_corpus.py --check    # fail if the corpus has moved

``--check`` runs in ``make verify-corpus``, so any edit to a specification, a
reference, an implementation or a label after freezing shows up as a failure
rather than as a silently better number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPECTRAP = REPO_ROOT / "spectrap"
LOCK = SPECTRAP / "CORPUS.lock"

# Everything that can change a ground-truth label or what a system is shown.
PATTERNS = [
    "tasks/*/SPEC.md",
    "tasks/*/SPEC.terse.md",
    "tasks/*/reference.py",
    "tasks/*/selftest.py",
    "tasks/*/crosscheck.py",
    "tasks/*/generators.py",
    "tasks/*/task.yaml",
    "cases/*/impl.py",
    "cases/*/self_tests.py",
    "cases/*/meta.yaml",
    "SPLIT.yaml",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    files: dict[str, str] = {}
    for pattern in PATTERNS:
        for path in sorted(SPECTRAP.glob(pattern)):
            files[path.relative_to(SPECTRAP).as_posix()] = digest(path)

    aggregate = hashlib.sha256()
    for name in sorted(files):
        aggregate.update(name.encode("utf-8"))
        aggregate.update(files[name].encode("ascii"))

    cases = sorted(p.parent.name for p in SPECTRAP.glob("cases/*/meta.yaml"))
    return {
        "version": 1,
        "n_files": len(files),
        "n_tasks": len(list(SPECTRAP.glob("tasks/*/task.yaml"))),
        "n_cases": len(cases),
        "corpus_sha256": aggregate.hexdigest(),
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    current = build()

    if args.check:
        if not LOCK.is_file():
            print(f"error: {LOCK} does not exist. Run `python scripts/freeze_corpus.py`.")
            return 1
        recorded = json.loads(LOCK.read_text(encoding="utf-8"))
        if recorded["corpus_sha256"] == current["corpus_sha256"]:
            print(
                f"corpus lock: OK  {current['n_cases']} case(s), "
                f"{current['n_files']} file(s), sha256={current['corpus_sha256'][:16]}"
            )
            return 0

        old, new = recorded.get("files", {}), current["files"]
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
        print("corpus lock: MISMATCH — the benchmark has changed since it was frozen.")
        for label, names in (("added", added), ("removed", removed), ("changed", changed)):
            for name in names[:20]:
                print(f"  {label}: {name}")
            if len(names) > 20:
                print(f"  ... and {len(names) - 20} more {label}")
        print(
            "\nIf this was intentional, re-freeze with `python scripts/freeze_corpus.py` "
            "and re-record the results; the two must move together."
        )
        return 1

    LOCK.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"froze {current['n_cases']} case(s) across {current['n_tasks']} task(s), "
        f"{current['n_files']} file(s)\n"
        f"corpus sha256 = {current['corpus_sha256']}\n"
        f"wrote {LOCK}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
