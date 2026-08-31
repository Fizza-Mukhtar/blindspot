#!/usr/bin/env python
"""Verify that the documentation only points at things that exist.

Rule Book #09 asks that every claim about results be connected to the evidence
submitted.  The cheapest way for that to go wrong is not dishonesty, it is
drift: a file gets renamed, a target gets removed, and a sentence written three
days earlier quietly becomes false.  A reader who follows one dead reference
starts doubting all the live ones.

So this walks every Markdown file and checks:

* every repository-relative path mentioned in backticks or a Markdown link
  actually exists (globs count as satisfied if they match anything);
* every ``make <target>`` mentioned is a real target in the Makefile;
* every ``blindspot <command>`` mentioned is a real subcommand;
* every ``pytest`` node id of the form ``file::test_name`` resolves.

Run with ``--strict`` to fail on the first problem; it is part of ``make check``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOCS = [
    "README.md",
    "REPRODUCE.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "PRIOR_ART.md",
    "PREREGISTRATION.md",
]
EXTRA_DOC_GLOBS = ["docs/*.md", "trajectories/README.md", "spectrap/*.md"]

# Backticked tokens that look like repository paths.
PATH_TOKEN = re.compile(
    r"`([A-Za-z0-9_][A-Za-z0-9_./*-]*\.[A-Za-z0-9]{1,6}|[a-z_]+/[A-Za-z0-9_./*-]*)`"
)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
# Only backticked or fenced invocations -- "make the comparison fair" is prose.
MAKE_TARGET = re.compile(r"`make ([a-z][a-z0-9-]*)`|^\s*make ([a-z][a-z0-9-]*)\s*$", re.M)
CLI_COMMAND = re.compile(r"`blindspot ([a-z][a-z0-9-]*)|^\s*blindspot ([a-z][a-z0-9-]*)", re.M)
PYTEST_NODE = re.compile(r"`([A-Za-z0-9_./-]+\.py)::([A-Za-z0-9_]+)`")

# Referenced deliberately as illustrations, not as files in this repository.
IGNORE = {
    "impl.py",
    "reference.py",
    "self_tests.py",
    "SPEC.md",
    "AUDIT.md",
    "meta.yaml",
    "task.yaml",
    "audit.json",
    "viewer.html",
    "requirements.txt",
    "pyproject.toml.lock",
    "e.g.",
    "i.e.",
    "etc.",
}
IGNORE_PREFIXES = ("http://", "https://", "mailto:", "spectrap/tasks/<", "results/runs/")


def doc_files() -> list[Path]:
    files = [REPO_ROOT / name for name in DOCS]
    for pattern in EXTRA_DOC_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(pattern)))
    return [f for f in files if f.is_file()]


def make_targets() -> set[str]:
    makefile = REPO_ROOT / "Makefile"
    if not makefile.is_file():
        return set()
    return set(re.findall(r"(?m)^([a-z][a-z0-9-]*):", makefile.read_text(encoding="utf-8")))


def cli_commands() -> set[str]:
    try:
        out = subprocess.run(
            [sys.executable, "-m", "blindspot.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        ).stdout
    except Exception:
        return set()
    match = re.search(r"\{([a-z0-9,-]+)\}", out)
    return set(match.group(1).split(",")) if match else set()


def path_exists(token: str, *, base: Path = REPO_ROOT) -> bool:
    """Resolve a documentation reference.

    Links are resolved relative to the document that contains them first (so
    `../README.md` inside `docs/` works), then relative to the repository root
    (so `results/summary.json` written from anywhere works).
    """
    if token in IGNORE or token.startswith(IGNORE_PREFIXES):
        return True
    if "*" in token or "?" in token:
        # `cassettes/**.json` is prose shorthand for "the json files under
        # cassettes/", not a literal pathlib glob, so normalise it.
        normalised = token.replace("**.", "**/*.")
        return any(REPO_ROOT.glob(normalised)) or any(REPO_ROOT.glob(token))
    return (base / token).resolve().exists() or (REPO_ROOT / token).exists()


def check() -> list[str]:
    problems: list[str] = []
    targets = make_targets()
    commands = cli_commands()

    for doc in doc_files():
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(REPO_ROOT).as_posix()

        for token in set(PATH_TOKEN.findall(text)) | set(MD_LINK.findall(text)):
            token = token.strip()
            if not token or token.startswith(IGNORE_PREFIXES) or token in IGNORE:
                continue
            # Bare names with no directory part are usually prose, not paths.
            if "/" not in token and not (REPO_ROOT / token).exists():
                continue
            if token.startswith("../") and (doc.parent / token).resolve().exists():
                continue
            if not path_exists(token, base=doc.parent):
                problems.append(f"{rel}: references missing path `{token}`")

        for groups in set(MAKE_TARGET.findall(text)):
            target = next((g for g in groups if g), "")
            if target and targets and target not in targets:
                problems.append(f"{rel}: references missing make target `make {target}`")

        for groups in set(CLI_COMMAND.findall(text)):
            command = next((g for g in groups if g), "")
            if command and commands and command not in commands:
                problems.append(f"{rel}: references unknown CLI command `blindspot {command}`")

        for file_part, test_name in set(PYTEST_NODE.findall(text)):
            candidate = REPO_ROOT / file_part
            if not candidate.is_file():
                problems.append(f"{rel}: pytest node names missing file `{file_part}`")
            elif f"def {test_name}(" not in candidate.read_text(encoding="utf-8"):
                problems.append(f"{rel}: `{file_part}` has no test named `{test_name}`")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any problem")
    args = parser.parse_args(argv)

    problems = check()
    if not problems:
        print(f"documentation references check: OK ({len(doc_files())} file(s))")
        return 0

    print(f"documentation references check: {len(problems)} problem(s)")
    for problem in sorted(problems):
        print(f"  {problem}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
