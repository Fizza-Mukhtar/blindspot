# Architecture

This document explains *why* the system is shaped this way. The rule throughout: a
component exists only if removing it changes a number, and every component listed here has
an ablation row in [CHANGELOG.md](CHANGELOG.md).

---

## The pipeline

```
   SPEC.md                                        impl.py
      │                                              │
      ▼                                              ▼
┌──────────────┐                            ┌────────────────┐
│ Cartographer │  spec ONLY                 │  Surface map   │  ast, no model
│              │  · barrier attested        │                │  signatures + raised
│              │  · quotes verified         │                │  exception types only
└──────┬───────┘                            └────────┬───────┘
       │ ObligationGraph                             │ SurfaceMap
       ▼                                             │
┌──────────────────┐                                 │
│  Ambiguity gate  │ ── unresolved ──► human queue   │
│  (human/policy)  │    (never a defect)             │
└──────┬───────────┘                                 │
       │ resolved obligations                        │
       └──────────────┬──────────────────────────────┘
                      ▼
              ┌───────────────┐   fan-out, one per obligation
              │   Adversary   │◄──── archetype memory (dev split only)
              └───────┬───────┘
                      ▼
              ┌───────────────┐
              │    Sandbox    │  isolated · no network · timeout · derandomised
              └───────┬───────┘
          ┌───────────┼────────────┐
       ERROR         PASS        FAIL
          │           │            │
   repair with     recorded,       ▼
   the traceback   not retried  ┌─────────┐
   (≤2 attempts)                │ Referee │  clause + input + observation ONLY
                                └────┬────┘
                        ┌────────────┼───────────┬──────────────┐
                     upheld      bad_test    ambiguous     out_of_domain
                        │         discard    → human          discard
                        ▼
                  ┌───────────┐
                  │ Minimiser │  model proposes, execution disposes
                  └─────┬─────┘
                        ▼
                  ┌───────────┐
                  │  Oracle   │  spec + ONE call · never sees the claim,
                  │           │  the clause, the probe or the code
                  └─────┬─────┘
                        │ ast.literal_eval comparison — no model adjudicates
             ┌──────────┴──────────┐
        agrees                 contradicts
             │                     │
             ▼                     ▼
            keep            withdraw the finding
                            (can only ever remove)
                        │
                        ▼
            AUDIT.md · repro/test_*.py · PR comment
```

---

## The six decisions that matter

### 1. The information barrier is enforced, not documented

An architecture diagram is not an enforcement mechanism. The Cartographer's context is
hashed, and every substantive line of the implementation is searched for inside it. If one
is found, the run raises `BarrierViolation` and stops. The attestation — context hash,
implementation hash, lines checked, lines leaked — is written into the trajectory, so the
claim is auditable rather than asserted.

Trivial lines (imports, short statements, bare `return`) are excluded from the check,
because they occur in unrelated prose by coincidence and a match on them would be noise.

**Why it is not "no information at all".** The adversary must be able to *call* the code,
so it receives a `SurfaceMap`: signatures, defaults, declared exception *types*, module
constants. Extracted with `ast`, never by a model. Docstrings are excluded by default —
they are author prose and can restate the very misreading the barrier exists to break.

### 2. Every inter-agent message is a validated schema

There are no free-text hand-offs. Each stage emits a Pydantic model, validated on receipt,
with a bounded repair loop that feeds the *exact* validation error back to the model
(`LLMRouter.structured`). A stage either produced a well-formed artefact or failed loudly.

`extra_validate` extends this to semantic checks. The Cartographer's verbatim-quote rule
is implemented as one: an obligation whose quote is not a contiguous substring of the
specification is rejected, named in the repair prompt, and dropped if it survives. **A
hallucinated requirement can never become an accusation.**

### 3. The sandbox distinguishes "wrong" from "broken"

pytest's exit code is not enough. The runner separates:

| Outcome | Meaning | What happens |
|---|---|---|
| `PASS` | no counterexample on this obligation | recorded, **not** retried — re-rolling until something turns red is how false alarms are manufactured |
| `FAIL` | candidate counterexample | goes to the referee |
| `ERROR` | the probe could not run: wrong signature, bad import, missing fixture, blocked socket | traceback returned to the adversary for repair; **never** counted as evidence |
| `TIMEOUT` | hung | discarded, obligation marked unprobed |

Determinism is part of the sandbox contract: `PYTHONHASHSEED=0`, a derandomised Hypothesis
profile, and **third-party pytest plugin autoloading disabled** — an installed plugin on
the development machine opened a socket during `pytest_configure`, which the network block
turned into a failure of every probe. Memory addresses, temp paths and timings are scrubbed
from captured output, because they would otherwise make byte-identical replay impossible.

### 4. Adjudication is a separate agent with strictly less context

The referee sees the clause, the input, and the observed failure. It does **not** see the
probe's source (which would invite it to agree with the probe's reasoning) or the
implementation (which would invite it to rationalise the behaviour). The
`failure_evidence()` helper strips the test source out of the pytest output, keeping only
the `E` lines and any Hypothesis falsifying example — so the promise the prompt makes is
one the code keeps.

Its calibration is deliberately asymmetric: default to `bad_test` when unsure. A missed
defect costs one finding; a false accusation costs the reader's trust in every finding.

### 5. The last word belongs to a reader that never saw the accusation

The Referee is shown the clause and the claim together, and that framing anchors it. On
the first live case a probe demanded that `resolve_range('bytes=500-500', 1)` return
`[(0, 0)]`, citing a clause that really does say an over-long *end* offset is clamped —
while another paragraph of the same document says a *start* offset past the end makes the
range unsatisfiable, and spells the asymmetry out in words. The Referee upheld it with the
clause in front of it, and upheld it again with the **entire specification** in front of
it. Adding context did not help, because it had already been told what the answer was
supposed to be.

So the Oracle removes the claim instead of adding context. It sees the specification and
one concrete call, and answers what that call should produce. It does not see the clause,
the probe, the implementation, the observed behaviour, or the expectation it is implicitly
checking. The comparison that follows is `ast.literal_eval` and an equality test — **no
model adjudicates anything.**

It is deliberately asymmetric: the Oracle can *withdraw* a finding and can never create
one. A stage whose job is protecting the reader's trust should only ever be able to remove
things from the report. `abl_no_oracle` prices it.

### 6. Human judgment has a designated place

Rule Book #04 and #05 ask for consequential actions to be gated and a qualified reviewer to
be part of the loop. In an auditing tool the consequential act is **accusing an engineer's
code of being wrong**, and the least safe place to automate that is a genuine gap in the
specification.

So: *an unresolved ambiguity is never reported as a defect.* Obligations resting on one are
withheld from probing entirely and surfaced as questions. `blindspot decide` walks a human
through them and writes answers to `decisions/<task_id>.yaml` — committed, reviewable,
replayable, keyed by a hash of the normalised question text so it survives the model
renumbering its ids.

---

## Reproducibility as an architectural constraint

Every model call goes through one door (`LLMRouter`) and is content-addressed on
`(system, user, model, temperature, max_tokens, purpose, nonce)`. The response is committed
to `cassettes/`.

Three properties fall out of that design:

- **Replay is free and offline.** `make reproduce` needs no key and no network. It is not
  *fast* — every generated test is genuinely re-executed against two targets — but the slow
  part is the part that cannot be faked.
- **Replay is order-independent, and this was not free.** The same prompt can legitimately
  recur inside one run, so recordings are stored as `<key>.<seq>.json` and the *n*-th
  occurrence replays the *n*-th recording. Those occurrence counters are scoped **by run
  id**. The first design kept one global counter and cleared it at the start of each run,
  which is correct in a serial sweep and wrong in a concurrent one: a reset from one job
  renumbered another job's in-flight lookups, and a replay could take a different path from
  the run it was replaying. It cost one run in 330 and it was found by comparing the
  per-case table rather than the summary. Now asserted in
  `tests/test_cassette_and_barrier.py::test_concurrent_runs_do_not_renumber_each_others_cassettes`.
- **Replay is verified, not assumed.** `make reproduce` re-runs everything and diffs the
  per-case outcome table against the committed one, because two runs can agree on a headline
  percentage while disagreeing about *which* cases they got right.
- **The cassettes are the trajectories.** Each file holds the full prompt and the full
  completion, so the reproducibility mechanism and the "agent trajectories" deliverable are
  the same artefact.

`provider` (transport) and `model_family` (model namespace) are deliberately separate
fields. Cassettes recorded through the Claude Code CLI are keyed on the model id `sonnet`;
if replay resolved model ids from the transport instead, it would look for `replay-smart`
and never find them. That bug existed, and
`tests/test_cassette_and_barrier.py::test_router_records_and_then_replays` is why it cannot
come back.

---

## Model backends

| Backend | Use | Credentials |
|---|---|---|
| `replay` *(default)* | reproducing published results | none |
| `claude_cli` | recording, via the Claude Code CLI headless | a Claude subscription |
| `anthropic` / `openai` | recording, via HTTP APIs | an API key |
| `mock` | the offline test suite | none |

Every call is **single turn** — one system prompt, one user message. That is a constraint,
not a limitation: it makes each call independently content-addressable, removes hidden
conversational state so a stage is a pure function of its inputs, and lets a coding agent
serve as a drop-in provider alongside raw HTTP.

---

## The benchmark harness

`spectrap/tasks/<id>/` is authored and committed:

| File | Role |
|---|---|
| `SPEC.md` | the ticket — the **only** file any evaluated system sees |
| `reference.py` | the hidden correct implementation; grader only |
| `generators.py` | domain-aware input sampler, biased to the corners the standard names |
| `selftest.py` | assertions traceable to the cited standard — the second, independent oracle |
| `crosscheck.py` | an independent re-derivation by an author who never saw `reference.py` |
| `task.yaml` | metadata, grounding URL, and two declared genuine ambiguities |

`spectrap/cases/<id>/` is forged: the model's `impl.py`, the tests that same model wrote for
it, and `meta.yaml` carrying the label and the witness. A case never duplicates `SPEC.md` or
`reference.py` — it points at its task, so there is one source of truth and drift is
impossible.

### The grader has no model in it

```
S_i = 1  iff  (∃ s ∈ T : exec(s, B) = FAIL)  ∧  (∀ s ∈ T : exec(s, R) = PASS)
```

Pure execution. The second conjunct is what stops `assert False` from scoring 100%. Every
credited counterexample is then re-executed four more times against both targets; anything
that does not agree with itself unanimously is discarded and counted as a flake.

---

## What was built and what was reused

Original to this submission: the orchestration, the cassette layer, the sandbox, the forge
and differential fuzzer, the grader, the statistics, the trajectory format and viewer, the
CLI, the corpus, and every prompt.

Reused, as published: `pydantic` (schemas), `PyYAML`, `rich` (CLI), `Jinja2`, `hypothesis`
(property-based probes), `pytest` (the execution substrate). No agent framework — the
orchestration is ~200 lines of `ThreadPoolExecutor` and typed messages, which is the whole
argument for not importing one.
