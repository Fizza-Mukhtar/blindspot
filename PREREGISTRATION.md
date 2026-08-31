# Pre-registration

**Written before the evaluation sweep was run. The central claim it registers was
refuted — see [§8](#8-deviations-from-this-plan).**

A benchmark built by the same person who builds the system that scores well on it deserves
scepticism. The strongest available answer is to write down what will be measured, on what
data, with which test, and what would count as a *negative* result — and to do it before
seeing any of the numbers.

That is what this is. Where the final results deviate from this plan, the deviation is
recorded in [§8](#8-deviations-from-this-plan) rather than quietly absorbed, and §8 opens by
reporting that the central claim failed.

**What backs the timing, and what does not.** This was written before the held-out sweep was
run, but the repository was assembled inside a single competition window and **its git
history is not a usable timestamp** — so do not take one on trust. What *is* checkable is
mechanical: [`spectrap/CORPUS.lock`](spectrap/CORPUS.lock) hashes every specification,
reference, implementation and label, `make verify-corpus` re-checks it, and the same lock
covers the split assignment in [`spectrap/SPLIT.yaml`](spectrap/SPLIT.yaml). The benchmark
that produced the numbers in §8 is provably the one described here, whatever order the
files were written in.

---

## 1. The claim under test

> When a language model writes both an implementation and its tests from the same
> specification, the two share one reading of it, so the tests pass when the reading is
> wrong. Deriving the obligations from the specification **with the implementation
> withheld** finds defects that the model's own suite, a direct prompt, and a
> general-purpose agent that reads the code all miss — without a higher false-alarm rate.

The claim has two halves and both are measured. A system that detects more defects by
accusing everything of everything has not supported it.

---

## 2. The frozen corpus

The benchmark is content-hashed in [`spectrap/CORPUS.lock`](spectrap/CORPUS.lock) —
a sha256 per file plus an aggregate digest. `make verify-corpus` re-checks it, so any edit
to a specification, reference, implementation or label after this point fails the build
instead of quietly improving a number.

- Split: drawn once by `blindspot split` with seed 20260828, **by task**, and frozen in
  [`spectrap/SPLIT.yaml`](spectrap/SPLIT.yaml) before any system was run. Splitting by task
  rather than by case means no implementation of a task the archetype memory was built from
  can appear in the held-out split.
- The **dev** split is the only data used to build archetype memory or to make any design
  decision.
- The **test** split is the pre-registered reporting set.

The exact counts as frozen are recorded in `CORPUS.lock` and restated in the README.

### Defect clustering, declared in advance

The forge generates several implementations per ticket, and more than one can fail on the
same witness input. These are distinct programs but **not independent observations**: a
system that reads the specification correctly gets all of them or none.

Therefore, alongside the per-case rate, the primary table reports an interval from a
**cluster bootstrap that resamples distinct defects**, and the number of distinct defects
is stated next to the number of cases. The clustered interval is the one to quote. This is
declared here because it is the analysis choice most able to flatter a result if chosen
after the fact.

---

## 3. Systems compared

All systems see the **same ticket rendition** the implementing model saw, run in the same
sandbox, and are graded by the same predicate.

| System | What it is |
|---|---|
| `self_tests` | the test suite the implementing model wrote for its own code. The floor. |
| `baseline_direct` | one call: ticket + implementation + *"write tests that find bugs."* No execution. |
| `baseline_agent` | a general-purpose ReAct agent with a sandbox and six rounds. **It reads the implementation body; Blindspot never does.** |
| `blindspot` | the full pipeline. |
| `abl_*` | one component removed at a time. |

`baseline_agent` is the honest bar. It has *more* information than Blindspot, not less, and
beating only `baseline_direct` would prove very little.

---

## 4. Primary endpoint

For a case *i* with candidate implementation `B_i`, hidden reference `R_i`, and the set `T`
of tests the system emitted:

```
S_i = 1  iff  (∃ s ∈ T : exec(s, B_i) = FAIL)  ∧  (∀ s ∈ T : exec(s, R_i) = PASS)
```

**Detection rate** = `Σ S_i / n_buggy`, over the test split.

The second conjunct is load-bearing and is why `assert False` scores zero rather than 100%.
A system is credited only when its accusation distinguishes *this* implementation from a
correct one.

No language model appears anywhere in this predicate. Every credited counterexample is
re-executed four additional times against both targets; a test that does not agree with
itself unanimously is discarded as a flake and never silently kept.

## 4b. Co-primary endpoint

**False-alarm rate** = fraction of *clean* cases on which the system reports a defect.

Detection and false alarms are reported together, always, and the headline summary statistic
is **Youden's J = detection − false alarms**. Reporting detection alone is not permitted by
this plan.

---

## 5. Secondary endpoints

- `detected_lenient` — at least one sound counterexample, ignoring other unsound tests.
- Unsound claims: emitted tests that fail on the hidden reference.
- Referee precision (`scripts/triage_audit.py`).
- Cost: model calls, content tokens, USD, wall clock.
- Per-ablation contribution, each against full Blindspot **restricted to the same cases**.

---

## 6. Statistical analysis

- **Intervals:** Wilson score for proportions; cluster bootstrap (10,000 resamples,
  seed 20260828) resampling distinct defects.
- **Paired comparison:** exact two-sided McNemar on the buggy cases, plus mid-p. Paired,
  because every system sees every case.
- **Multiplicity:** ablation comparisons are secondary and Holm-adjusted.
- **Effect size:** paired percentage-point difference with a percentile bootstrap interval.

**This benchmark is small and will stay small.** With a handful of distinct defects the
power ceiling is low, and where no discordant pair exists McNemar cannot reach significance
at any α. The plan is therefore to report the power ceiling explicitly and to describe
results as **directional evidence**, never as a significance claim. A large p-value here is
a statement about `n`, not about the intervention.

---

## 7. What would count against the claim

Stated in advance so it cannot be redefined later. Any of these is a negative result and
will be reported as one:

1. `blindspot` does not exceed `baseline_agent` on detection at equal or lower false alarms.
2. The `abl_no_barrier` ablation matches full Blindspot. The barrier is the central claim;
   if removing it costs nothing, the thesis is unsupported and the architecture is
   ceremony.
3. `blindspot`'s false-alarm rate exceeds `baseline_direct`'s. A more sensitive detector
   that is also noisier is not an improvement for the intended user.
4. Detection gains vanish once outcomes are clustered by distinct defect.

---

## 8. Deviations from this plan

### 8.1 The pre-registered claim failed

Run on the held-out split, the pre-registered configuration triggered condition 1 of
[§7](#7-what-would-count-against-the-claim):

| System | Detection | On spec violations | False alarms | Youden J |
|---|---|---|---|---|
| The model's own suite | 0/9 | 0/2 | 0/26 | 0.00 |
| Baseline A — one direct prompt | 4/9 = 44% | 0/2 | 11/26 = 42% | +0.02 |
| Baseline B — general agent with tools | **5/9 = 56%** | 1/2 | 9/26 = 35% | +0.21 |
| **Blindspot (pre-registered)** | **1/9 = 11%** | 0/2 | **1/26 = 4%** | +0.07 |

Withholding the implementation from the test generator did **not** find defects the
baselines miss. It found far fewer. The claim in §1 is not supported, and no amount of
reframing changes that; it is reported first, in the README, and in the table above.

What the barrier *did* buy is the other half of §1: precision. **4% false alarms against
35–42%, and 1 unsound claim against 5–7** — the best precision of any system measured, on a
system that found almost nothing to be precise about.

These are the numbers as finally frozen. Earlier drafts of this section quoted slightly
different ones, because three defects in the *measurement* were still being found at the
time — a sandbox timeout counted as an observation (iteration 24), a trajectory writer that
could kill the run it was logging (iteration 29), and a cassette counter shared across
concurrent runs (iteration 30). Each is in the changelog with its fix. None of them changed
the direction of the result.

### 8.2 What the diagnosis found, and what it did not

The obvious suspect was over-filtering — the Oracle was added late and can only remove
findings. It was not the cause: across the whole run the Oracle withdrew **one** finding.

The actual mechanism is visible in the trajectories. On a missed case, ten probes ran and
**ten passed**. Working from the specification alone, the adversary never proposed the
input that separates the implementation from the reference. The barrier that keeps the
implementation's misreading out of the *oracle* also blinds the *search*.

### 8.3 The deviation: three post-hoc configurations

All three are labelled post-hoc wherever they appear, and all are reported **alongside** the
pre-registered configuration, never instead of it.

**`blindspot_targeted`** — the adversary may read the implementation when choosing *inputs*,
while the obligation it tests against still comes from the barrier-attested, spec-only
Cartographer. Validated on the dev split, where it moved detection from 0/7 to 2/7 at
unchanged false alarms.

**That dev result did not replicate.** Re-running the identical configuration on dev gave
0/7. The variance was later traced to two real defects in the measurement — a sandbox
timeout being counted as an observation, and a cassette counter shared across concurrent
runs (changelog iterations 24 and 30). The configuration is implemented and registered, but
**it is not in the reported sweep**, because promoting a configuration on a dev result that
does not reproduce is exactly the mistake this document exists to prevent.

**`blindspot_search`** — the adversary is told to *search* the input domain with a
`hypothesis` property rather than pick a single input. No extra information: it still never
sees the implementation. **Rejected on dev** (0/7, unchanged) and reported on test anyway,
for completeness rather than promotion, where it confirms the dev finding at 1/9. The
directive demonstrably worked — property-based probes rose from 8% to 50% of the
adversary's output — and detection did not move. A negative result about a plausible idea
is worth reporting.

**`agent_plus_oracle`** — the general-purpose agent's tests, filtered by the Oracle alone.
If the transferable contribution is a specification-anchored reading that never sees the
accusation, it should improve a *better* generator than ours. The Oracle can only remove a
test, so detection cannot rise artificially by adding findings; it rises only when removing
an unsound test stops that test from disqualifying a sound one under the ∀-clause in §4.

**This one worked.** 6/9 against `baseline_agent`'s 5/9 at an identical false-alarm rate of
9/26, and 2/2 against 1/2 on the cases that are genuine specification violations. It is a
single case flip on nine cases with four distinct defects — directional evidence with a
visible mechanism, not a significance claim — and the mechanism is legible in one
trajectory: `agent_plus_oracle--discount_stacking__v12.jsonl`, where one withdrawal
converts a miss into a detection.

### 8.35 A validity problem in the benchmark itself

Chasing the negative result turned up something that undercuts the endpoint in §4 rather
than the system: **`has_defect` does not mean "violates the specification".** It is
assigned by differentially fuzzing the candidate against the hand-written reference, so it
means "differs from the reference somewhere". Two correct implementations differ freely
wherever the specification is silent.

Executing each task's authoritative, standard-traced `selftest.py` against every buggy
implementation separates the two:

| | buggy cases | specification violations | differences only |
|---|---|---|---|
| whole corpus | 16 | **3** | 13 |
| test split | 9 | **2** | 7 |
| dev split | 7 | 1 | 6 |

This is now a first-class label — `spec_visible` in every `meta.yaml`, computed by
execution in `scripts/label_spec_visible.py` and carried into `results/per_case.csv` — and
it is reported alongside the pre-registered endpoint rather than replacing it.

It changes how §8.1 should be read. **Four of the five detections that put
`baseline_agent` ahead are on cases where the specification determines nothing**, so what
distinguishes it there is agreement with the reference author, not conformance. A system
built to accuse only when the specification fixes the answer is *correct* to stay silent on
those, and the endpoint has no way to say so.

**The pre-registered endpoint is still reported as the primary**, because changing the
primary endpoint after seeing the numbers is exactly what pre-registration exists to
prevent. But it is reported as an endpoint now known to be measuring something other than
what §1 claimed to be about, and the spec-visible subset — 2 held-out cases, which supports
no conclusion — is reported next to it.

### 8.4 Honest status of the post-hoc work

The decision to investigate was taken **after** seeing the aggregate held-out numbers in
§8.1. That is unblinding, and it is why:

- the pre-registered configuration remains the headline row;
- the diagnosis used trajectories and the **dev** split, not per-case test outcomes;
- `blindspot_targeted` was accepted on dev evidence before being run on test;
- no case label, no split assignment and no grading rule was changed at any point — the
  corpus hash in `spectrap/CORPUS.lock` is the same one frozen before §8.1 was run.

A reader who thinks the post-hoc rows should be discounted entirely is entitled to; the
pre-registered row is reported in full so that they can.

### 8.5 Disclosed before the sweep

For completeness, these live runs happened **before** this pre-registration and informed
the engineering, so they are not blind:

- A one-case smoke evaluation (`results/smoke/`) which revealed that the barrier
  attestation was aborting every run.
- A single-case audit of `http_range_resolve__v0`, repeated while fixing the referee. This
  case motivated the Oracle stage. Its ground-truth label was never edited, and the fix was
  to the *system*, not to the case — but the design of the Oracle was informed by seeing
  one held-out case fail, and that is disclosed rather than hidden.
- A one-case run of `baseline_agent` (`results/agent_smoke/`) which revealed that the
  baseline had been silently scoring zero.

No detection or false-alarm number from any of those runs appears in the reported results,
and no case label was changed as a result of them.
