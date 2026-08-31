# Are the terse tickets fair?

Every SpecTrap task ships **two renditions of the same requirements**:

| | |
|---|---|
| `spectrap/tasks/<task>/SPEC.md` | the *detailed* rendition — numbered rules, bold headings, a worked-examples table |
| `spectrap/tasks/<task>/SPEC.terse.md` | the *terse* rendition — the same requirements as a working engineer writes them, in running prose |

Across the 14 tasks the terse rendition averages **57%** of the detailed one's length
(range 53–68%).

This document exists because the obvious objection to a benchmark like this one is:
*"you rewrote the specifications until the model failed."* That objection deserves a real
answer rather than an assurance, so here is the rule that was applied, the procedure that
enforced it, the mechanical guard that backs it, and the part that remains a human
judgement.

---

## Why there are two renditions at all

The detailed rendition came first, and the corpus built from it was **too easy**. Both a
large and a small model implemented those specifications correctly almost every time
(`results/forge_report.json`, and iteration 5 of the [Improvement Changelog](../CHANGELOG.md)).
A benchmark where the defect rate is near zero measures nothing.

The reason was visible in the documents themselves. A specification that says

> ## Promotion after rounding
>
> **This is the part the old quota-email code got wrong.** Rounding happens *before* the
> label is attached…

has done the hard part of the reader's job for them. It has located the trap, labelled it,
and pointed at it. Real tickets do not do this — if the author already knew which clause
would be missed, they would have said so, and the bug would not exist. **The signposting
was the artefact, not the difficulty.**

So the terse rendition is not "the specification, but harder". It is the specification
written the way the ticket that produces this bug in real life is written.

---

## The rule

> A terse rendition may change **how** a requirement is presented. It may not change
> **whether** the requirement is stated.

Concretely, what is allowed and what is not:

| Allowed | Not allowed |
|---|---|
| Folding a numbered rule into a sentence | Deleting a rule |
| Removing a heading that names the trap | Making a stated behaviour unstated |
| Dropping the worked-examples table, keeping the decisive examples inline | Dropping an example that is the *only* thing fixing an answer |
| Moving a clause out of prominent position into a subordinate clause | Introducing a new requirement the detailed rendition lacks |
| Citing a standard by number and URL where the detailed text quoted it | Citing a standard *instead of* stating a requirement the standard leaves open |

The test a rendition must pass is **determination**: for every assertion in the task's
authoritative `selftest.py`, a careful reader with the terse ticket (and the standards it
cites) must be able to derive the asserted answer. If they could not, the requirement was
written back in — at a cost to the length ratio, which is why the ratios are not uniform.

---

## The procedure

For each task, every assertion in `selftest.py` was walked one at a time and marked
`DETERMINED` or `NOT DETERMINED` against the terse text alone. Where an assertion came out
`NOT DETERMINED`, the terse rendition was amended until it did, and the amendment was
recorded.

Six of these audits are shipped in full as `spectrap/tasks/<task>/SPEC.terse.audit.md`.
They are not summaries: each one names the trap sentence verbatim, counts the assertions
checked, records which requirements had to be restored, and — importantly — lists the
places where the author was *not* fully confident. For example, the `semver_sort` audit
flags that four of its twelve assertions are determined only if the reader follows the
linked Semantic Versioning standard rather than reading the ticket in isolation, and says
exactly which four.

That residual uncertainty is left visible on purpose. "Determined" is a judgement about
what a careful reader can derive, and no amount of process turns it into a mechanical
fact.

---

## The mechanical guard

What *is* mechanical is this: **both renditions share one authoritative test suite and one
reference implementation.**

`spectrap/tasks/<task>/selftest.py` is written against the requirements, not against
either rendition's wording, and `make verify-corpus` runs it against `reference.py` in CI.
So:

- If a terse rendition had quietly dropped a requirement, the requirement would still be
  in `selftest.py`, and the reference would still have to satisfy it. The corpus's
  ground-truth labels are therefore rendition-independent by construction.
- A case's `meta.yaml` records which rendition produced it (`spec_variant`), so the two
  conditions are never pooled by accident.
- The auditor under evaluation is shown **the same rendition the implementer was shown**.
  Neither side gets the more explicit document.

The one thing the guard cannot catch is a terse rendition that is *under*-determined in a
way `selftest.py` happens not to assert. That is what the human audits are for, and why
they ship.

---

## What it changed, measured

Ticket style turned out to be a variable worth reporting rather than a knob to tune, so
both conditions are kept and reported separately. The green-and-wrong rate by rendition —
how often a model's implementation is provably wrong while its own test suite is green —
is in `results/forge_report.json` and summarised in the
[README](../README.md#3-the-forge-the-benchmark-builds-itself).

---

## If you disagree

The detailed renditions are still in the repository, still forged, and still evaluated.
Every result can be recomputed on the `detailed` cases alone:

```bash
python -c "import csv;rows=[r for r in csv.DictReader(open('results/per_case.csv')) ] ; print(len(rows))"
```

and `spectrap/cases/*/meta.yaml` carries `spec_variant` on every case, so the split is one
filter away. If the terse condition is unconvincing to you, drop it — the detailed
condition is a complete, self-contained benchmark on its own, and the README reports it
separately for exactly that reason.
