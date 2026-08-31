#!/usr/bin/env python
"""Check that every arXiv citation in the documentation is a real paper.

`PRIOR_ART.md` claims that every reference was fetched from the arXiv API and
verified rather than recalled.  A claim like that is worth exactly as much as
the command that re-checks it, so this is that command.

For each `arxiv.org/abs/<id>` referenced anywhere in the Markdown, it queries
the arXiv API and reports the real title.  A fabricated or mistyped id comes
back with no entry and fails the run.

    python scripts/verify_citations.py            # list every citation + title
    python scripts/verify_citations.py --strict   # exit non-zero if any is bogus

This is the one check that needs the network, which is why it is deliberately
*not* part of `make check` — that has to stay runnable offline.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARXIV = re.compile(r"arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})")
API = "http://export.arxiv.org/api/query?"


def cited_ids() -> dict[str, list[str]]:
    """Map each arXiv id to the documents that cite it."""
    found: dict[str, list[str]] = {}
    for path in sorted(REPO_ROOT.rglob("*.md")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for arxiv_id in set(ARXIV.findall(text)):
            found.setdefault(arxiv_id, []).append(path.relative_to(REPO_ROOT).as_posix())
    return found


def title_of(arxiv_id: str, *, timeout: float = 30.0) -> tuple[bool, str | None]:
    """Return ``(reached_the_api, title)``.

    The two failure modes must not be confused. A query that reaches arXiv and
    comes back with no entry means **the paper does not exist**; a query that
    never arrives means nothing at all. Reporting a network outage as a
    fabricated citation would be its own kind of false accusation.
    """
    url = API + urllib.parse.urlencode({"id_list": arxiv_id, "max_results": 1})
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return (False, None)
    match = re.search(r"<entry>.*?<title>(.*?)</title>", body, re.S)
    if not match:
        return (True, None)
    title = " ".join(match.group(1).split())
    # arXiv answers an unknown id with a placeholder entry titled "Error".
    if title.lower().startswith("error"):
        return (True, None)
    return (True, title)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = parser.parse_args(argv)

    citations = cited_ids()
    if not citations:
        print("no arXiv citations found")
        return 0

    print(f"verifying {len(citations)} arXiv citation(s) against the live API\n")
    bad: list[str] = []
    unreachable: list[str] = []
    for arxiv_id in sorted(citations):
        reached, title = title_of(arxiv_id)
        where = ", ".join(citations[arxiv_id])
        if not reached:
            print(f"  {arxiv_id}  ?? could not reach arXiv (network or rate limit) [{where}]")
            unreachable.append(arxiv_id)
        elif title is None:
            print(f"  {arxiv_id}  ** NO SUCH PAPER ** cited in {where}")
            bad.append(arxiv_id)
        else:
            print(f"  {arxiv_id}  OK  {title[:76]}")
        time.sleep(args.delay)

    print()
    if bad:
        print(f"{len(bad)} citation(s) do not resolve to a paper: {', '.join(bad)}")
    if unreachable:
        print(f"{len(unreachable)} citation(s) could not be checked; re-run when online.")
    if not bad and not unreachable:
        print("every citation resolves to a real paper.")
    return 1 if (bad and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
