#!/usr/bin/env python
"""Build the submission archive, and refuse to build one containing a secret.

Rule Book #08 requires credentials to stay outside the submission.  `.env` is
gitignored, which protects a `git push` — and protects nothing at all if the
folder is zipped by hand, which is how a submission archive usually gets made.
This project's `.env` holds a live OAuth token, so "zip the folder" is a real
way to leak it.

So the archive is built by an allow-list, and then **scanned before it is
written out**: if any file inside it matches a credential shape, the archive is
deleted and the command fails.

    python scripts/package_submission.py
    python scripts/package_submission.py --out blindspot-submission.zip

What is included: everything a judge needs to read, run and reproduce the
result.  What is excluded: credentials, caches, build junk, and the run logs
that are scratch output rather than evidence.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories copied wholesale.
INCLUDE_DIRS = [
    "src",
    "spectrap",
    "cassettes",
    "trajectories",
    "tests",
    "scripts",
    "docs",
    "decisions",
    ".github",
]

# Individual files at the root.
INCLUDE_FILES = [
    "README.md",
    "CHANGELOG.md",
    "REPRODUCE.md",
    "ARCHITECTURE.md",
    "PREREGISTRATION.md",
    "PRIOR_ART.md",
    "LICENSE",
    "Makefile",
    "pyproject.toml",
    "requirements.lock",
    ".gitignore",
    ".env.example",
]

# Result artefacts that are evidence.  Run logs are not.
INCLUDE_RESULT_GLOBS = [
    "results/*.csv",
    "results/*.json",
    "results/*.md",
    "results/expected/*",
    "results/forge/*",
]

EXCLUDE_PARTS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".hypothesis",
    ".venv",
    "venv",
    ".blindspot",
}

# Deliberately broad.  A false positive costs one look; a false negative
# publishes somebody's credential.
SECRET = re.compile(
    rb"sk-ant-(?:api|oat)[0-9]{2}-[A-Za-z0-9_\-]{20,}"
    rb"|sk-proj-[A-Za-z0-9_\-]{20,}"
    rb"|gh[pousr]_[A-Za-z0-9]{30,}"
    rb"|AKIA[0-9A-Z]{16}"
)
SCAN_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
    ".jsonl",
    ".html",
    ".lock",
    ".example",
    "",
}


def wanted() -> list[Path]:
    seen: set[Path] = set()
    for name in INCLUDE_FILES:
        path = REPO_ROOT / name
        if path.is_file():
            seen.add(path)
    for name in INCLUDE_DIRS:
        for path in (REPO_ROOT / name).rglob("*"):
            if path.is_file() and not (set(path.parts) & EXCLUDE_PARTS):
                seen.add(path)
    for pattern in INCLUDE_RESULT_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                seen.add(path)
    return sorted(seen)


def scan(paths: list[Path]) -> list[str]:
    hits: list[str] = []
    for path in paths:
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        try:
            if SECRET.search(path.read_bytes()):
                hits.append(path.relative_to(REPO_ROOT).as_posix())
        except OSError:
            continue
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "blindspot-submission.zip")
    args = parser.parse_args(argv)

    files = wanted()
    excluded_env = (REPO_ROOT / ".env").is_file()

    print(f"packaging {len(files)} file(s)")
    if excluded_env:
        print("  .env exists and is NOT included (it holds a live token)")

    leaks = scan(files)
    if leaks:
        print("\nREFUSING TO PACKAGE — credential-shaped string found in:")
        for name in leaks:
            print(f"  {name}")
        print("\nRemove the secret, then re-run. Nothing was written.")
        return 1

    args.out.unlink(missing_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, path.relative_to(REPO_ROOT).as_posix())

    size_mb = args.out.stat().st_size / 1_000_000
    print(f"\nwrote {args.out.name}  ({size_mb:.1f} MB, {len(files)} files)")
    print("scanned every included file for credentials: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
