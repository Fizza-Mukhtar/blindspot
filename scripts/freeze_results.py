#!/usr/bin/env python
"""Promote a freshly recorded sweep to the committed reference results.

``make reproduce`` replays the cassettes and asserts the outcome table matches
``results/expected/``.  That assertion is only meaningful if the reference was
produced deliberately, so promoting it is an explicit step rather than a side
effect of running the evaluation:

    make record      # live, writes results/ and cassettes/
    make freeze      # copy results/ -> results/expected/ and checksum it
    make reproduce   # offline, must now agree exactly

A checksum manifest is written alongside so that a later reader can tell
whether the committed reference has been edited by hand since it was frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "results"
DEFAULT_TARGET = REPO_ROOT / "results" / "expected"

# Only the files the reproduction assertion reads.  Logs, scratch directories
# and the forge report are deliberately not frozen: they are evidence about how
# the corpus was built, not part of the claim being reproduced.
FROZEN_FILES = ["per_case.csv", "summary.json", "records.json", "RESULTS.md"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)

    missing = [name for name in FROZEN_FILES if not (args.source / name).is_file()]
    if missing:
        print(
            f"error: {args.source} is not a complete sweep; missing {', '.join(missing)}.\n"
            "Run `make eval` (offline) or `make record` (live) first.",
            file=sys.stderr,
        )
        return 1

    args.target.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    for name in FROZEN_FILES:
        source = args.source / name
        shutil.copy2(source, args.target / name)
        manifest[name] = sha256_file(source)
        print(f"froze {name}  sha256={manifest[name][:16]}")

    (args.target / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nwrote {args.target / 'SHA256SUMS.json'}")
    print("Now run `make reproduce` to confirm the offline replay agrees.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
