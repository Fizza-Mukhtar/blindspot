# How this corpus was built

Every case in `spectrap/cases/` was produced by `blindspot forge`. Nothing was hand-written
and nothing was hand-selected: a variant is admitted only when the mechanical admission
rule fires. This file records the exact commands, in order, so the corpus can be rebuilt
and so the reader can see what was *tried* — including the passes that produced nothing.

The frozen result is hashed in [`CORPUS.lock`](CORPUS.lock) and checked by
`make verify-corpus`.

---

## The admission rule

For each generated variant, in this order:

1. The model writes an implementation from the ticket.
2. The **same model**, in a separate call that does not see its own reasoning, writes a
   test suite for that implementation.
3. Its own suite is executed. **Red → discarded.** Those are defects CI already catches,
   and they are not what this benchmark is about.
4. The implementation is differentially fuzzed against the hand-written reference, and the
   task's authoritative `selftest.py` is run against it.
5. A witness input on which the two disagree makes the case **buggy**; no disagreement
   under the fuzzing budget makes it **clean**.

No label is assigned by a language model, and none by inspection.

---

## The passes, in order

```bash
# 1 — detailed tickets, the first corpus
blindspot forge --provider claude_cli --record \
    --variants 4 --clean-per-task 2 --buggy-per-task 1

# 2 — terse tickets, both quotas (see ../docs/SPEC_FAIRNESS.md for why)
blindspot forge --provider claude_cli --record --spec-variant terse \
    --variants 6 --buggy-per-task 2 --clean-per-task 1 \
    --impl-model fast --variant-offset 20

# 3 — terse tickets, hunting defects only (the clean quota was already full)
blindspot forge --provider claude_cli --record --spec-variant terse \
    --variants 8 --buggy-per-task 4 --clean-per-task 0 \
    --impl-model fast --variant-offset 40

# 4 — the nine tasks that had produced no defect at all
blindspot forge --provider claude_cli --record --spec-variant terse \
    --variants 10 --buggy-per-task 3 --clean-per-task 0 \
    --impl-model fast --variant-offset 60 \
    --only allocate_money csv_rfc4180 currency_quantize iso_week_date \
           keyset_paginate merge_intervals rbac_authorize rollout_bucketing token_bucket
```

`--variant-offset` keeps case ids unique across passes. Forging is idempotent: a pass that
finds a task's quota already full skips it, so re-running the sequence does not grow the
corpus.

---

## What the passes actually produced

Pass 4 admitted **nothing**. Ten implementations each of nine tasks, and not one was
green-and-wrong: the model either got them right or its own tests caught it. That is a
result, not a failure of the pass — those nine specifications are ones this model does not
misread — and it is why the corpus concentrates on five tasks rather than fourteen.

**A bug found while running pass 4.** The first attempt produced nothing *at all*, and the
reason was not the tasks: prompts go out at temperature 0, and the style list that varied
them had only four entries, so variants 4–11 were byte-identical requests that hit their
own cassette and replayed the first implementation. `--variants 12` silently meant four.
Fixed with a caller-supplied nonce and a longer style list (iteration 20 of the
[Improvement Changelog](../CHANGELOG.md)); pass 4 above is the re-run.

That fix changed every forge prompt's cache key, which means **passes 1–3 can no longer be
replayed from their cassettes** — their recordings are keyed under the old scheme. Rather
than quote summary statistics whose artefact cannot be regenerated, the forge's headline
numbers come from a separate, single, pre-specified **census run** described below. The
corpus itself is unaffected: it is the frozen cases in `cases/`, hashed in `CORPUS.lock`.

---

## The census

One clean pass over **all fourteen tasks**, terse tickets, six implementations each,
written to a scratch directory so it cannot alter the frozen corpus:

```bash
blindspot forge --provider claude_cli --record --spec-variant terse \
    --variants 6 --buggy-per-task 99 --clean-per-task 99 \
    --impl-model fast --variant-offset 100 \
    --label census-haiku-terse --out results/census_cases
```

Quotas are set high so that nothing is skipped and every variant is measured. This is the
only source for the green-and-wrong rate quoted in the README, and it is reproducible from
its own cassettes: `results/forge/census-haiku-terse.json` (copied to
`results/forge_report.json`, which is what generates the README's numbers).

What it found, across **84 implementations of 14 tickets**:

| | count |
|---|---|
| implementations generated | 84 |
| own test suite red — discarded, CI already catches these | 28 |
| own test suite green | 56 |
| **green and provably wrong** | **9** |
| **green-and-wrong rate** | **16%** |
| model-written suites that *reject the correct reference* | 16 |
| cases where the two independent oracles disagreed (flagged, never silently resolved) | 8 |

The last two rows are about the *tests* rather than the code, and they are the ones worth
sitting with. Roughly one suite in five, written by a model for its own code, fails a
correct implementation of the same ticket. A green suite and a red suite are both weak
evidence on their own.

---

## The consequence for the statistics

Because several implementations of one ticket can fail on the same witness, the corpus
contains **more buggy cases than distinct defects**. Those outcomes are correlated, so
`trap_id` — `(task, witness)` — is carried through to `results/per_case.csv`, and every
detection interval is also computed by resampling *defects* rather than cases. Both counts
are reported side by side; the clustered one is the honest one.
