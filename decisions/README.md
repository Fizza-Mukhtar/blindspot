# The human checkpoint

Rule Book #04 and #05 require consequential actions to be gated behind human approval, and
a qualified human reviewer to be part of any solution that could significantly affect
someone. In an auditing tool the consequential act is **telling an engineer their code is
wrong**, and the place where that judgement is least safe to automate is a genuine gap in
the specification.

So the rule is absolute and it is enforced in code, not in prose:

> **An unresolved ambiguity is never reported as a defect.**

An obligation that rests on a question the specification does not settle is *withheld from
probing entirely* (`ObligationGraph.resolved_obligations`), and the question is escalated
to a person instead.

## What the published run escalated

Across the held-out and dev splits, Blindspot raised **93 escalations covering
53 distinct questions** over 14 tickets. They are real
specification-lawyer questions, not padding — a representative one:

> *Since Python's `bool` is a subclass of `int`, does passing `True`/`False` as `length`
> count as a valid "int of zero or more", or must it be rejected?*

Every one of them is in the trajectories as a `human.checkpoint` event with its options and
its `resolved_by` status.

## What the published run decided

**Nothing.** This directory contains no `<task_id>.yaml`, so every one of those questions
stayed `unresolved`, and every obligation depending on one stayed unprobed. That is the
conservative default, and it is part of why Blindspot's false-alarm rate is the lowest of
any system measured — it declines to accuse on anything the specification does not settle.

Shipping it undecided is deliberate. A benchmark run is exactly the situation where there
is no qualified human to ask, and inventing answers would have quietly converted "the spec
is silent" into "the implementation is wrong" — the failure this whole project is about.

## How to decide them

```bash
blindspot decide byte_units      # walks you through the open questions, one at a time
```

That writes `decisions/<task_id>.yaml`: a committed, reviewable, replayable artefact, so a
team answers each question once rather than once per pull request. Answers are keyed by a
hash of the *normalised question text* rather than by the run-assigned id, because ids are
regenerated every run while the question a specification leaves open is stable.

[`byte_units.yaml.example`](byte_units.yaml.example) shows the format, populated with three
questions this system actually raised. It has an `.example` suffix so it is **not** loaded:
resolving a question changes what the agent probes, and the published cassettes were
recorded with everything unresolved.
