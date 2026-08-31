# Agent trajectories

One `.jsonl` file per run, named `<system>--<case_id>.jsonl`. Append-only, one JSON object
per step, readable top to bottom as a narrative.

**The fastest way in:** open `viewer.html` — a single self-contained file with every
trajectory inlined. No server, no CDN, no account, works offline. Regenerate it with
`make trace`.

```bash
make trace                 # writes trajectories/viewer.html
head -c 2000 trajectories/blindspot--<case>.jsonl | python -m json.tool  # or just read it
```

---

## Start with these four

Read in this order. Together they cover the pipeline working, the pipeline finding nothing,
the comparison the original claim rested on, and the one stage that actually earned its
place.

### 1. The pipeline, start to finish — `blindspot--discount_stacking__v11.jsonl`

The whole pipeline working. Follow the steps in order:

| Step | Event | What to look at |
|---|---|---|
| 1 | `run.start` | the config fingerprint and every ablation flag, so the run is identifiable |
| 2 | `stage.start` | note: *"spec-only: the implementation is not in this context"* |
| 3 | `tool.call` `barrier_attest` | **the attestation** — implementation lines checked, lines leaked (0), and the hash of the exact context. This is the barrier being *enforced*, not described. |
| 4 | `llm.call` `cartographer` | the full agent instructions and the obligation ledger it produced. Every `quote` here was verified by string match against the spec. |
| — | `agent.decision` | any obligation dropped for an unverifiable quote |
| — | `human.checkpoint` | one per ambiguity, with `resolved_by: unresolved` meaning *escalated, not reported as a defect* |
| — | `tool.call` `ast.extract_surface` | exactly what crossed the barrier: signatures and exception types, no bodies |
| — | `llm.call` `adversary` | one per obligation; the probe and its stated intent |
| — | `tool.call` `sandbox.run_probe` | the probe's source and the sandbox's verdict |
| — | `llm.call` `referee` | adjudication with strictly less context than the probe had |
| last | `run.end` | verdict, findings, and the cost record |

### 2. An instructive failure — `blindspot--http_range_resolve__v0.jsonl`

Search for `verify.retry` and for `agent.decision` events whose `what` starts with
`triage ... -> bad_test`. These are the interesting steps: the adversary produced a red
test, and the referee *refused it*. Read the referee's `reason` — it is the system
declining to make an accusation the specification does not support, which is the behaviour
the false-alarm rate exists to reward.

Also look for `reason: "probe_not_runnable"` retries: the sandbox handed back a traceback
and the adversary repaired its own call. That is feedback shaping the next step, and it is
counted as a tool failure rather than as evidence about the code.

### 3. The comparison the original claim rested on — same case, two systems

```
blindspot--discount_stacking__v11.jsonl          barrier ON
abl_no_barrier--discount_stacking__v11.jsonl     barrier OFF, everything else identical
```

Open both in the viewer and compare the **first `llm.call`**. Same system prompt, same
schema, same agent role. The only difference is that the second one has `impl.py` appended
to its context — and the `stage.start` note says so. Then compare the obligation ledgers
that come back.

Whatever the detection rate does between these two runs is the value of the information
boundary, separated from the value of having a separate role at all. In the published run
it does almost nothing, because the configuration it is measuring detects almost nothing —
an ablation cannot tell you what a component is worth when the system it is removed from is
already at the floor. That is stated in the results table rather than glossed.

### 4. The stage that earned its place — `agent_plus_oracle--discount_stacking__v12.jsonl`

This is the one to read if you only read one.

The general-purpose agent emitted two tests for this case. One was a sound counterexample;
the other asserted something the specification does not require, and **under the grading
rule a single unsound test disqualifies the whole case** — the agent scored nothing here.

Search the file for `oracle.second_opinion`. The Oracle is handed the specification and one
concrete call, and never sees the test, its author's reasoning, or the implementation. It
predicts what the call should produce; the comparison against the test's assertion is
`ast.literal_eval`, with no model adjudicating. It disagrees, the test is withdrawn, and
the surviving counterexample is credited.

One withdrawal, one case converted from a miss into a detection, and no false alarm added —
because a stage that can only *remove* a test cannot manufacture a finding. Follow it with
`agent.decision` whose `what` reads `demoted ... upheld -> bad_test`.

---

## What is here, and why some of it is not in the results table

Every run of every system, on both splits — 443 files, not a curated sample. The brief asks
for *representative* trajectories; this is all of them, because selecting which runs a judge
may inspect is not a decision the author of a benchmark should be making.

Two things in here are deliberately kept even though they do not appear in
`results/summary.json`:

- **`blindspot_targeted--*`** — a post-hoc configuration that let the adversary read the
  implementation when choosing inputs. It moved dev detection from 0/7 to 2/7, and then the
  identical configuration re-run on dev gave 0/7. It was **dropped rather than promoted**,
  because the dev result did not reproduce. The trajectories are the evidence that the
  experiment happened and how it looked; the reasoning is changelog iteration 23.
- **`*--<dev-split case>`** — runs on the tuning split. They are how design decisions were
  made, and they are not part of any reported number.

`forge.jsonl` is the corpus construction itself: every implementation and every
model-written test suite, with the prompt that produced it.

## Format

Plain JSONL. Field names follow the OpenTelemetry GenAI semantic conventions where they
apply, so the files can be ingested by standard tooling — but the format stays plain text
on purpose, because a judge should be able to read it with `head`.

| Event | Meaning |
|---|---|
| `run.start` / `run.end` | run boundaries, config, verdict, cost |
| `stage.start` / `stage.end` | pipeline stage boundaries with a summary |
| `llm.call` | one model call: `prompt.system` (the agent's instructions), `prompt.user`, `completion`, `gen_ai.usage.*`, and the `cassette` it replayed from |
| `tool.call` | a deterministic action: `sandbox.run_probe`, `ast.extract_surface`, `barrier_attest`. Includes the full arguments and the full response. |
| `verify.retry` | feedback that changed the next step: `schema_violation`, `semantic_violation`, `probe_not_runnable`, `provider_error` |
| `human.checkpoint` | an ambiguity, its options, and whether a human resolved it |
| `agent.decision` | a choice the orchestrator made, with its reason |

Two conventions worth knowing:

- **`cassette` is a filename.** Every `llm.call` names the recording it replayed, so any
  step can be traced to `cassettes/<...>.json`, which holds the same prompt and completion
  independently. The reproducibility mechanism and the trajectory are the same artefact.
- **Long fields are truncated** at 24,000 characters with an explicit marker. Nothing is
  summarised or paraphrased; the cassette holds the untruncated text.

---

## Which runs are here

Every `(system, case)` pair from the last sweep, including all baselines and all ablations,
so a claim about any system can be checked against its own trace rather than against a
summary. `forge.jsonl` records corpus construction; `demo--*.jsonl` is written by
`make demo`.
