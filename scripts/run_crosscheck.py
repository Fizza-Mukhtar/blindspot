#!/usr/bin/env python
"""Differentially compare each reference implementation against an independent oracle.

Motivation
----------
SpecTrap's references and their standard-traceable selftests were written
together.  That is exactly the correlated-authorship risk this whole project is
about, so the corpus is held to the same standard it holds others to: every
reference was re-derived a second time, from ``SPEC.md`` and the cited standard
alone, by an author who never saw the reference -- and the two are then
differentially fuzzed against each other.

A disagreement is one of three things, and the *standard* is the tiebreaker:

  (a) the independent oracle is wrong          -> fix crosscheck.py
  (b) the reference is wrong                   -> a real corpus bug, must be fixed
  (c) SPEC.md does not determine the behaviour -> a corpus design problem

This pass found four class-(b) bugs in the references (Python's ``\\d`` matching
non-ASCII numerals, and ``$`` matching before a trailing newline).  They are
fixed; see CHANGELOG.md.

Usage
-----
    python scripts/run_crosscheck.py                 # every task with an oracle
    python scripts/run_crosscheck.py semver_sort     # one task
    python scripts/run_crosscheck.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from blindspot.corpus import Task, load_tasks  # noqa: E402
from blindspot.sandbox.runner import RunStatus, SandboxSpec, run  # noqa: E402

DRIVER = '''\
import copy
import json
import random

import crosscheck
import generators
import reference

ENTRY = {entry!r}
BUDGET = {budget}

ref_fn = getattr(reference, ENTRY)
oracle_fn = crosscheck.oracle


def call(fn, args, kwargs):
    """Observable outcome, plus whether the callee mutated its own arguments.

    A pure function that rewrites its input is a defect the differential
    comparison alone would miss, because both sides could return the same value.
    """
    frozen = copy.deepcopy((args, kwargs))
    live_args, live_kwargs = copy.deepcopy((args, kwargs))
    try:
        value = fn(*live_args, **live_kwargs)
        outcome = ("return", repr(value))
    except Exception as exc:  # noqa: BLE001
        outcome = ("raise", type(exc).__name__)
    mutated = (live_args, live_kwargs) != frozen
    return outcome, mutated


report = {{
    "known_values": [],
    "disagreements": [],
    "mutations": [],
    "checked": 0,
    "notes": getattr(crosscheck, "ORACLE_NOTES", ""),
}}

# --- 1. values the oracle's author derived from the standard, against BOTH ----
for entry in getattr(crosscheck, "KNOWN_VALUES", []):
    args, kwargs, expected = entry
    ref, _ = call(ref_fn, args, kwargs)
    orc, _ = call(oracle_fn, args, kwargs)
    if isinstance(expected, tuple) and len(expected) == 2 and expected[0] == "raises":
        want = ("raise", expected[1])
    else:
        want = ("return", repr(expected))
    report["known_values"].append(
        {{
            "args": repr(args)[:400],
            "kwargs": repr(kwargs)[:200],
            "expected": list(want),
            "reference": list(ref),
            "oracle": list(orc),
            "reference_ok": ref == want,
            "oracle_ok": orc == want,
        }}
    )

# --- 2. differential fuzz ------------------------------------------------------
inputs = list(getattr(generators, "SEEDS", []))
rng = random.Random(20260828)
for _ in range(BUDGET):
    try:
        inputs.append(generators.sample(rng))
    except Exception:
        break

for args, kwargs in inputs:
    report["checked"] += 1
    ref, ref_mutated = call(ref_fn, args, kwargs)
    orc, orc_mutated = call(oracle_fn, args, kwargs)
    if ref_mutated and len(report["mutations"]) < 5:
        report["mutations"].append({{"who": "reference", "args": repr(args)[:300]}})
    if orc_mutated and len(report["mutations"]) < 5:
        report["mutations"].append({{"who": "oracle", "args": repr(args)[:300]}})
    if ref != orc:
        report["disagreements"].append(
            {{"args": repr(args)[:500], "kwargs": repr(kwargs)[:200],
              "reference": list(ref), "oracle": list(orc)}}
        )
        if len(report["disagreements"]) >= 12:
            break

print("@@XCHECK@@" + json.dumps(report))
'''


def crosscheck_task(task: Task, *, budget: int, timeout_s: float) -> dict:
    path = task.directory / "crosscheck.py"
    if not path.is_file():
        return {"task_id": task.task_id, "status": "missing"}

    result = run(
        SandboxSpec(
            files={
                "reference.py": task.reference_src,
                "generators.py": task.generators_src,
                "crosscheck.py": path.read_text(encoding="utf-8"),
                "driver.py": DRIVER.format(entry=task.entrypoint, budget=budget),
            },
            entry="driver.py",
            runner="script",
            timeout_s=timeout_s,
            max_output_chars=2_000_000,
        )
    )
    if result.status is RunStatus.TIMEOUT:
        return {"task_id": task.task_id, "status": "timeout"}
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("@@XCHECK@@")), None)
    if line is None:
        return {
            "task_id": task.task_id,
            "status": "error",
            "detail": (result.stderr or result.stdout)[-2000:],
        }

    payload = json.loads(line[len("@@XCHECK@@") :])
    payload["task_id"] = task.task_id
    payload["status"] = "ok"
    known = payload["known_values"]
    payload["known_total"] = len(known)
    payload["known_reference_fail"] = [k for k in known if not k["reference_ok"]]
    payload["known_oracle_fail"] = [k for k in known if not k["oracle_ok"]]
    payload["agreed"] = not payload["disagreements"] and not payload["known_reference_fail"]
    return payload


def render(payload: dict, *, verbose: bool) -> None:
    task_id = payload["task_id"]
    status = payload["status"]
    if status != "ok":
        print(f"[{status.upper():>7}] {task_id}  {payload.get('detail', '')[:400]}")
        return

    mark = " ok " if payload["agreed"] else "FAIL"
    print(
        f"[{mark}] {task_id}: {payload['checked']} inputs compared, "
        f"{len(payload['disagreements'])} disagreement(s); known values "
        f"{payload['known_total'] - len(payload['known_reference_fail'])}"
        f"/{payload['known_total']} on the reference, "
        f"{payload['known_total'] - len(payload['known_oracle_fail'])}"
        f"/{payload['known_total']} on the oracle"
    )
    for entry in payload["known_reference_fail"]:
        print(
            "        ! REFERENCE disagrees with a standard-derived value\n"
            f"          input   : {entry['args']} {entry['kwargs']}\n"
            f"          expected: {entry['expected']}\n"
            f"          got     : {entry['reference']}"
        )
    for entry in payload["disagreements"][: (12 if verbose else 3)]:
        print(
            f"        ~ input   : {entry['args']} {entry['kwargs']}\n"
            f"          reference: {entry['reference']}\n"
            f"          oracle   : {entry['oracle']}"
        )
    for entry in payload.get("mutations", []):
        print(f"        ! {entry['who']} mutated its input on {entry['args']}")
    if payload["known_oracle_fail"] and verbose:
        print(f"        (the oracle failed {len(payload['known_oracle_fail'])} of its own values)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", help="task ids; default is every task")
    parser.add_argument("--budget", type=int, default=4000)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    tasks = [t for t in load_tasks() if not args.tasks or t.task_id in args.tasks]
    if not tasks:
        print("no matching tasks", file=sys.stderr)
        return 2

    payloads = [crosscheck_task(t, budget=args.budget, timeout_s=args.timeout) for t in tasks]
    for payload in payloads:
        render(payload, verbose=args.verbose)

    present = [p for p in payloads if p["status"] == "ok"]
    agreed = [p for p in present if p["agreed"]]
    missing = [p for p in payloads if p["status"] == "missing"]
    total_inputs = sum(p["checked"] for p in present)
    print(
        f"\n{len(agreed)}/{len(present)} references agree with their independent oracle "
        f"across {total_inputs:,} compared inputs"
        + (f"; {len(missing)} task(s) have no oracle" if missing else "")
    )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payloads, indent=2) + "\n", encoding="utf-8")
    return 0 if len(agreed) == len(present) else 1


if __name__ == "__main__":
    raise SystemExit(main())
