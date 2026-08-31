# Blindspot

**AI writes the code. AI writes the tests. Both come from the same reading of the same
specification — so when the reading is wrong, the tests agree with the bug and CI goes
green.** That much is measured here and it holds: on this benchmark a model's own test
suite catches **0 of 9** defects in its own code, while wrongly rejecting a *correct*
implementation **24 times**.

Blindspot was the proposed fix: derive what the specification *demands* before being
allowed to see what the code *does*, then try to prove the code wrong — reporting a finding
only when it can produce a test that fails on the implementation and passes a reference it
has never seen.

## The result, first

**The fix as designed does not work. Repairing it produced something better, and the
repair's diagnosis is the most useful thing here.**

The hypothesis was pre-registered — endpoint, analysis plan, and the exact conditions that
would refute it — in [`PREREGISTRATION.md`](PREREGISTRATION.md), before the held-out split
was run. Two of those conditions fired. Blindspot detects **1 of 9** held-out defects
against a general-purpose agent's 5. Withholding the implementation from the test generator
does not sharpen it; it blinds it.

But the repair does work, and it is the useful half of the result: moving the barrier off
the *search* and onto the *oracle* alone beats that agent — **6 of 9 at exactly its own
false-alarm rate**, and it is the only system that catches both of the defects that are
genuine specification violations.

Chasing that produced the finding this repository is actually for:

> **A benchmark built by differentially fuzzing an implementation against a reference does
> not measure conformance. It measures *mimicry of the reference*.**
>
> Executing each task's authoritative, standard-traced test suite against every "buggy"
> implementation shows that **13 of 16 carry no specification violation at all** — they
> satisfy every requirement the specification pins down and differ from the reference only
> where it is silent. **4 of the 5 detections that make the baseline look good are on those
> cases.** A verifier that accuses only when the specification determines the answer scores
> zero on such a benchmark, and it is *right* to.

Differential fuzzing against a reference is a common way to build agent evaluations. If you
build one that way, this is what you are grading.

Everything below — the agent, the forge, the grader, the ablations — is the instrument that
produced those numbers, and every one of them replays offline from committed recordings,
with no API key and no network.

**The short version.** The problem is real and measured. The proposed solution is refuted
and reported as refuted. The repaired solution beats the strongest baseline. And the
benchmark that measured all three turns out to be measuring something other than what it
appeared to.

---

## For judges — the four deliverables

| Required deliverable | Where it is |
|---|---|
| **1. Solution code + improvement changelog** | this repository · [`CHANGELOG.md`](CHANGELOG.md) (the Improvement Changelog, one entry per experiment, with evidence) |
| **2. Reproduction guide** | [`REPRODUCE.md`](REPRODUCE.md) — clean-environment walkthrough, exact commands, runtimes, cost |
| **3. Solution video (≤5 min)** | submitted with the entry. Every frame of it is reproducible here: `python scripts/demo.py --case full_jitter_backoff__v12` is the walkthrough it shows, and `make reproduce` regenerates every number it quotes |
| **4. Agent trajectories** | [`trajectories/`](trajectories/) — JSONL per run + a self-contained `viewer.html` (double-click, no server). Curated entry points in [`trajectories/README.md`](trajectories/README.md) |
| Agent instructions | [`src/blindspot/prompts/`](src/blindspot/prompts/) — every system prompt as a reviewable Markdown file |
| **Pre-registration** | [`PREREGISTRATION.md`](PREREGISTRATION.md) — the endpoint, the analysis plan and what would count as a *negative* result, written before the sweep ran |
| Prior art & honest differentiation | [`PRIOR_ART.md`](PRIOR_ART.md) — every citation verified against the arXiv API |
| Architecture | [`ARCHITECTURE.md`](ARCHITECTURE.md) |

**The one command that matters:**

```bash
make reproduce-quick     # headline systems      ~15 min
make reproduce           # everything, ablations ~40 min
```

No API key. No network. No Docker. Both replay every model call from committed cassettes
and **fail loudly if anything drifts** — they compare the per-case outcome table, not just
the summary. Neither is fast, and the reason is worth knowing: the *model* calls are
replayed instantly, but every generated test is genuinely re-executed against both the
candidate and the hidden reference. The slow part is the part that cannot be faked.

---

## 1. The problem

### Who has it

Anyone reviewing code they did not write, where a model wrote both the code and its tests.
That is now the default: an engineer opens a pull request produced by a coding agent, sees
a green suite, and has to decide whether the green means anything.

Concretely, the user this is built for is **the reviewer on a pull request they did not
author** — and the second user is the engineer who wrote the ticket and needs to know
whether the thing that came back actually does what they asked.

### The bottleneck

A test suite is only as good as the understanding that produced it. When the same model,
from the same prompt, writes both the implementation and its tests, the two share a
*single* reading of the specification. If that reading is wrong, the tests encode the same
error and pass.

The reviewer's only remaining defence is to re-derive the specification's requirements by
hand and check each one — which is exactly the slow, easy-to-skip work that the agent was
supposed to remove. So it gets skipped, and the failure mode is silent: no red build, no
stack trace, just an implementation that is confidently wrong on the inputs nobody tried.

This is not speculation. Every link in the chain is published — LLM oracles capture a
program's *actual* rather than *expected* behaviour
([arXiv:2410.21136](https://arxiv.org/abs/2410.21136)); conditioning test generation on the
code changes what the tests find ([arXiv:2409.09464](https://arxiv.org/abs/2409.09464));
pass rates fall sharply under stronger suites
([EvalPlus](https://arxiv.org/abs/2305.01210)). What is *not* published is the joint
measurement, so this project measures it. See [The forge](#3-the-forge-the-benchmark-builds-itself).

### Why solving it matters

Green CI is the signal the entire review pipeline is built on. If it has quietly become a
measurement of *correlation between two model outputs* rather than of *correctness*, then
every downstream control — code review, staged rollout, on-call — inherits a false
negative it cannot see.

---

## 2. The hypothesis

> **Test independence is an information-flow property, not an org-chart property.**

Most multi-agent test systems separate *responsibilities*: a writer agent and a tester
agent, each with its own persona. Both still read the code. Blindspot separates
*information*.

**This section describes what was built and why. [§5](#5-results) describes what happened
when it was measured, which is not what this section predicted.** The hypothesis was
pre-registered — endpoint, analysis plan, and what would count as a refutation — in
[`PREREGISTRATION.md`](PREREGISTRATION.md), before the held-out split was ever run. It was
refuted, the refutation is the most useful thing in this repository, and it is reported
before anything else.

The architecture:

```
  SPEC.md ──► Cartographer ──► obligation ledger ──► Ambiguity gate ──┐
              (spec ONLY,          (every quote      (human decides,  │
               never the code)      verified)         or it is        │
                                                      withheld)       ▼
  impl.py ──► Surface map ────────────────────────────────────► Adversary
              (ast: signatures only,                                  │
               not behaviour)                                         ▼
                                                                  Sandbox
                                         ERROR ──► repair with traceback ─┐
                                         PASS  ──► recorded, not retried  │
                                         FAIL  ──► Referee ──► Minimiser ──► Oracle ─┴─► Finding
                                                                            (withdraws
                                                                             false ones)
```

Five design choices carry the system, and **each one is switched off in an ablation so its
contribution is a number rather than a claim**:

1. **The information barrier.** The Cartographer reads `SPEC.md` and nothing else. This is
   *enforced and attested*: the exact bytes of its context are hashed and checked against
   the implementation source, and the run aborts if any substantive line of the code
   appears. The attestation is written into the trajectory, so it is verifiable rather than
   promised.

2. **Verified quotes.** Every obligation must carry a **verbatim contiguous substring** of
   the specification. The check is a string match — no model in the loop — and an
   obligation whose quote cannot be found is dropped. A hallucinated requirement can never
   become an accusation.

3. **The ambiguity gate (the human checkpoint).** Questions the specification genuinely
   does not settle are routed to a person via `blindspot decide`, and obligations resting
   on an unresolved question are **withheld from probing entirely**. An unsettled question
   is escalated, never reported as a defect.

   In the published run this fired **93 times, on 53 distinct questions across all 14
   tickets** — real ones, like *"since Python's `bool` is a subclass of `int`, does
   `length=True` count as a valid length?"* **None of them was answered**, because a
   benchmark run is precisely the situation with no qualified human to ask, and inventing
   answers would have converted "the specification is silent" into "the implementation is
   wrong". See [`decisions/`](decisions/README.md). This is Rule Book #04/#05 implemented
   as a code path rather than promised in prose.

4. **Adjudication.** A red test is a *claim*, not a defect. The Referee sees the clause,
   the input and the observed failure — but not the test's source and not the
   implementation — and decides: real defect, bad test, genuine ambiguity, or out of
   domain. Its calibration is deliberately asymmetric, because a false accusation costs the
   reader's trust in every other finding.

5. **An independent oracle that never sees the accusation.** Adjudication alone was not
   enough. The Referee is handed the clause and the claim *together*, and that anchors it:
   on the first live case it upheld a probe demanding `resolve_range('bytes=500-500', 1)`
   return `[(0, 0)]`, and went on upholding it when handed the entire specification, which
   states in words that a start offset past the end is unsatisfiable. Being shown the right
   text did not help, because it had already been told what the answer should be.

   So the Oracle **removes the claim** rather than adding context: it sees the specification
   and one concrete call, and works out what that call should produce — no clause, no probe,
   no implementation, no observed behaviour. Its answer is compared to the test's assertion
   with `ast.literal_eval`, so **no model adjudicates anything**. It can only ever withdraw
   a finding, never create one.

### What comes out

Not a document — a **runnable pytest file** with the minimal failing input and the clause it
violates, plus a PR-ready comment. `blindspot audit --format pr` prints something you can
paste into a review.

---

## 3. The forge: the benchmark builds itself

The obvious objection to any self-built defect benchmark is *"you wrote the bugs and the
detector."* The forge removes the author from that loop.

1. A model is given `SPEC.md` **and nothing else** and asked to implement the ticket the way
   it normally would. It does not know a benchmark exists.
2. The **same model** is then shown its own implementation and asked to write the test suite
   that ships with it — precisely the workflow that produces the failure.
3. Those tests are executed. A case is admitted **only if they are green**, because a red
   suite is the easy case CI already catches.
4. The implementation is differentially fuzzed against a hidden, hand-written reference. A
   concrete disagreement is the *buggy* label; no disagreement within the published budget
   is the *clean* label.
5. An independent second oracle — assertions traceable to the cited standard — is run too.
   Where the two oracles disagree, the case is **flagged, never silently labelled**.
6. Finally, the task's authoritative suite is executed against the implementation and its
   verdict is recorded on the case: `spec_visible` distinguishes a **specification
   violation** from a difference where the specification is merely silent. It is
   re-derivable at any time with [`scripts/label_spec_visible.py`](scripts/label_spec_visible.py)
   and checked by `make verify-corpus`.

**Step 6 was added last, and it is the step that mattered.** Steps 1–5 are the standard way
to build a defect corpus, and on their own they produce a benchmark of *differences from a
reference* — most of which violate nothing. That is the finding in [§9](#9-hot-take), and
the forge is the thing that made it visible.

**No label is ever assigned by a language model, and none by inspection.** The exact commands that built the corpus, what each pass produced, and the pass that produced *nothing*, are in [`spectrap/PROVENANCE.md`](spectrap/PROVENANCE.md).

<!-- BEGIN:forge -->
- **84** implementations generated from **14** tickets, each with a test suite written by the same model that wrote the code.
- **28** were discarded because their own tests were red — CI already catches those.
- Of the **56** whose own suite was green, **9** were provably wrong — a green-and-wrong rate of **16%**.
- **16** of the model-written suites *reject the correct reference implementation* — they encode a misreading strongly enough to fail correct code.
- **8** cases where the two independent labelling oracles disagreed (flagged, never silently resolved).
<!-- END:forge -->

### The tasks

14 pure, deterministic Python functions whose specifications contain a requirement that is
**stated plainly but easy to skim past**. The traps are not invented for this benchmark —
each is a clause of a published standard that implementations routinely get wrong:

| Task | The trap | Grounded in |
|---|---|---|
| `semver_sort` | numeric pre-release identifiers rank *below* alphanumeric ones; build metadata is excluded from precedence, making ties observable | [semver.org 2.0.0](https://semver.org/spec/v2.0.0.html) §10–11 |
| `http_range_resolve` | offsets are inclusive; an overrun `last-byte-pos` is *clamped*, not a 416 | [RFC 7233](https://www.rfc-editor.org/rfc/rfc7233.html#section-2.1) §2.1 |
| `allocate_money` | largest-remainder allocation; the parts must sum to the total exactly, including for negatives | [Fowler, Money](https://martinfowler.com/eaaCatalog/money.html) |
| `token_bucket` | refill is continuous and fractional; the accrual mark advances on **denied** requests too | [RFC 2697](https://datatracker.ietf.org/doc/html/rfc2697) |
| `rbac_authorize` | deny overrides unconditionally — beating order *and* specificity; no match means deny | [XACML 3.0](https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html) |
| `csv_rfc4180` | quotes are doubled not escaped; spaces are data, not a reason to quote | [RFC 4180](https://datatracker.ietf.org/doc/html/rfc4180#section-2) §2 |
| `iso_week_date` | the week-numbering year is not the calendar year (`2021-01-01` → `2020-W53-5`) | [ISO 8601 week date](https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar) |
| `merge_intervals` | half-open `[a,b)` means adjacent intervals **must** merge; zero-length ones are dropped first | [EWD 831](https://www.cs.utexas.edu/~EWD/transcriptions/EWD08xx/EWD831.html) |
| `keyset_paginate` | the cursor must key on the full `(created_at, id)` tuple or rows are silently dropped | [use-the-index-luke](https://use-the-index-luke.com/no-offset) |
| `rollout_bucketing` | builtin `hash()` is per-process salted; salting by percentage breaks monotonicity mid-ramp | [PYTHONHASHSEED](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED) |
| `discount_stacking` | percentages compound multiplicatively (20% then 10% is 28% off, not 30%) | [Shopify discount combinations](https://help.shopify.com/en/manual/discounts/discount-combinations) |
| `full_jitter_backoff` | the cap bounds the *ceiling of the random range*, not the drawn result; there is no additive base | [AWS: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) |
| `currency_quantize` | the minor-unit exponent is not always 2 (JPY 0, KWD 3, CLF 4); ties are half-even on an exact `Decimal` | [ISO 4217](https://www.iso.org/iso-4217-currency-codes.html) |
| `byte_units` | SI kilo is lowercase `kB` = 1000; IEC is `KiB` = 1024 | [IEC binary prefixes](https://www.iec.ch/prefixes-binary-multiples) |

Each task also carries **two genuine under-determinations**, declared in `task.yaml`. They
are not defects, and a system that reports them as defects is penalised. They exist so the
ambiguity gate has something real to catch.

### The corpus checks itself

The references and their standard-traceable tests were written together, which is the very
correlated-authorship risk this project is about. So the corpus is held to its own standard:
**every reference was independently re-derived from the specification and the cited standard
by an author who never saw it**, and the two are differentially fuzzed against each other.

```bash
make verify-corpus   # 154 mechanical integrity checks across the 14 tasks
make crosscheck      # each reference vs. an independent spec-blind oracle
```

---

## 4. How it is scored

One pre-registered primary endpoint, defined as an **execution predicate**. For a case *i*
with the candidate implementation `B`, the hidden reference `R`, and the set `T` of tests
the system emitted:

```
S_i = 1   iff   (∃ s ∈ T : exec(s, B) = FAIL)   ∧   (∀ s ∈ T : exec(s, R) = PASS)

DR = ΣS_i / n_buggy        FAR = ΣFA_j / n_clean        J = DR − FAR
```

**The second conjunct is load-bearing.** Without it, `assert False` scores 100% — it fails on
every implementation. Requiring every emitted test to pass on the hidden reference means a
system is credited only when its accusation is *sound*: it distinguishes **this** code from a
correct one. There is a test for exactly this in
[`tests/test_grader.py`](tests/test_grader.py) (`test_assert_false_scores_zero`).

**No language model appears anywhere in the scoring path.** The referee assigns a triage
*category*; no reported metric is a function of that category.

**Determinism gate.** Every credited counterexample is re-executed four more times against
both targets. A test that does not agree with itself unanimously is discarded and counted
as a flake — never silently kept. A sandbox *timeout* is treated as an inconclusive
measurement and retried with more headroom, not as a disagreement: before that fix the
headline numbers moved depending on how loaded the machine was (changelog iteration 24).

### Two labels, and why the difference is the whole story

| label | how it is assigned | what it means |
|---|---|---|
| `has_defect` | differential fuzzing against the hidden reference | the implementation **differs from the reference** somewhere |
| `spec_visible` | the task's authoritative, standard-traced `selftest.py` is executed against the implementation | the implementation **violates a stated requirement** |

`has_defect` is the pre-registered endpoint's notion of a defect, and it is weaker than it
looks: a specification determines some of a function's behaviour and leaves the rest open,
so two *correct* implementations differ freely in the gap. `spec_visible` is computed by
execution in [`scripts/label_spec_visible.py`](scripts/label_spec_visible.py), checked by
`make verify-corpus`, and carried into `results/per_case.csv`.

Most of this corpus's defects are the first kind and not the second. That is the finding in
[§9](#9-hot-take), and it is why the results table reports both.

**Statistics** ([`src/blindspot/eval/stats.py`](src/blindspot/eval/stats.py), pure stdlib):
Wilson score intervals; exact conditional McNemar with mid-p for paired outcomes; a
percentile bootstrap for the effect size; Holm correction on the secondary comparisons.

<!-- BEGIN:power -->
> **The power ceiling, stated before the result.** With 9 held-out buggy cases carrying 4 distinct defects, and zero baseline-only wins, exact two-sided McNemar gives *p* = 2^(1-b) — so **6** system-only wins are required to reach *p* < 0.05, however large the difference looks. SpecTrap is powered to detect only large effects. Everything below is a directional signal, not a significance claim.
<!-- END:power -->

**The split was frozen before any system was run against it** — a seeded shuffle, the seed
and procedure committed in [`spectrap/SPLIT.yaml`](spectrap/SPLIT.yaml). All prompt and
design iteration used the 4-task dev split.

---

## 5. Results

Read this table with three things in mind, all of which are consequences of measurement
rather than caveats added afterwards:

1. **The pre-registered system (`blindspot`) fails.** It is reported first and in full.
2. **The detection column is not a conformance measure** — see the spec-violations column
   next to it, and [§9](#9-hot-take) for why.
3. **One configuration does beat the fair baseline**, and it is not the one the project set
   out to build: `agent_plus_oracle` takes the code-reading agent's tests and filters them
   through the specification-anchored Oracle. Same false alarms, more detections, and it is
   the only system that catches both genuine specification violations.

<!-- BEGIN:results -->
| System | What it is | Detection (95% CI) | ...resampling defects | On spec violations only | False alarms (95% CI) | Youden J | Runs that errored |
|---|---|---|---|---|---|---|---|
| The model's own test suite | the floor | **0/9 = 0%** [0, 30] | [0, 0] | 0/2 | 0/26 = 0% [0, 13] | +0.00 | 0/35 |
| Baseline A — one direct prompt | spec + code, one call, no execution | **4/9 = 44%** [19, 73] | [0, 100] | 0/2 | 11/26 = 42% [26, 61] | +0.02 | 0/35 |
| Baseline B — general agent + sandbox | ReAct loop, 6 rounds, sees the code | **5/9 = 56%** [27, 81] | [10, 100] | 1/2 | 9/26 = 35% [19, 54] | +0.21 | 0/35 |
| Blindspot (pre-registered) | information barrier on *everything*; never sees the code | **1/9 = 11%** [2, 44] | [0, 50] | 0/2 | 1/26 = 4% [1, 19] | +0.07 | 0/35 |
| Blindspot + search-first probes | same barrier; told to search rather than guess (post-hoc) | **1/9 = 11%** [2, 44] | [0, 50] | 0/2 | 3/26 = 12% [4, 29] | -0.00 | 0/35 |
| **Agent + spec-anchored Oracle** | agent picks the inputs; barrier on the oracle only (post-hoc) | **6/9 = 67%** [35, 88] | [18, 100] | 2/2 | 9/26 = 35% [19, 54] | +0.32 | 0/35 |

The 9 buggy cases in the held-out split carry **4 distinct defects** — the forge generates several implementations per ticket and more than one can fail the same way. Those outcomes are correlated, so the fourth column resamples *defects* rather than cases. It is the wider interval, and it is the one to quote.

**Read the spec-violations column before the detection column.** `has_defect` is assigned by differentially fuzzing the candidate against the reference, so it means *differs from the reference*, not *violates the specification*. Executing each task's authoritative standard-traced suite against every buggy case shows most of them violate nothing the specification states -- they differ only where it is silent. That column counts detections on the cases that genuinely are specification violations. It is a tiny subset and supports no conclusion on its own; it is there because the detection column, read alone, is misleading. See [the hot take](#9-hot-take).

The last column is there because of a bug this table would otherwise have hidden: a stage that crashes and falls back to passing its input through is indistinguishable, in every other column, from a stage that ran and changed nothing. A system with errored runs is not reporting a result about its design; it is reporting a result about its reliability.

**blindspot vs baseline_direct** on 9 paired buggy cases: b = 0 system-only wins, c = 3 baseline-only wins; exact two-sided McNemar p = 0.25 (mid-p = 0.125), **not** significant at α = 0.05. Δ = -33 pp ([-67, 0] bootstrap).

**blindspot vs baseline_agent** on 9 paired buggy cases: b = 0 system-only wins, c = 4 baseline-only wins; exact two-sided McNemar p = 0.125 (mid-p = 0.0625), **not** significant at α = 0.05. Δ = -44 pp ([-78, -11] bootstrap).

**blindspot_search vs baseline_direct** on 9 paired buggy cases: b = 0 system-only wins, c = 3 baseline-only wins; exact two-sided McNemar p = 0.25 (mid-p = 0.125), **not** significant at α = 0.05. Δ = -33 pp ([-67, 0] bootstrap).

**blindspot_search vs baseline_agent** on 9 paired buggy cases: b = 0 system-only wins, c = 4 baseline-only wins; exact two-sided McNemar p = 0.125 (mid-p = 0.0625), **not** significant at α = 0.05. Δ = -44 pp ([-78, -11] bootstrap).

**agent_plus_oracle vs baseline_direct** on 9 paired buggy cases: b = 2 system-only wins, c = 0 baseline-only wins; exact two-sided McNemar p = 0.5 (mid-p = 0.25), **not** significant at α = 0.05. Δ = +22 pp ([0, 56] bootstrap).

**agent_plus_oracle vs baseline_agent** on 9 paired buggy cases: b = 1 system-only wins, c = 0 baseline-only wins; exact two-sided McNemar p = 1.0 (mid-p = 0.5), **not** significant at α = 0.05. Δ = +11 pp ([0, 33] bootstrap).
<!-- END:results -->

Per-case outcomes for every system and every case are in
[`results/per_case.csv`](results/per_case.csv), so every statistic above can be recomputed
from the raw table. `scripts/triage_audit.py` puts every finding that reached a reader next
to the grader's independent verdict on it.

**How the Oracle earns its column.** The grading rule disqualifies a case if *any* emitted
test fails on the hidden reference, so a single unsound test throws away a sound
counterexample sitting beside it. On `discount_stacking__v12` the agent emitted exactly that
pair; the Oracle — which sees the specification and the call, never the test or the
implementation — disagreed with the unsound one, withdrew it, and the surviving
counterexample was credited. One withdrawal, one case converted from a miss to a detection,
no false alarm added, because a stage that can only *remove* a test cannot manufacture a
finding. The trajectory is
[`agent_plus_oracle--discount_stacking__v12.jsonl`](trajectories/README.md).

### Which design choices actually earned their place

<!-- BEGIN:ablations -->
| Configuration | Detection | Δ | False alarms | Δ | n cases |
|---|---|---|---|---|---|
| remove the **information barrier** (same roles, spec-reader also sees the code) | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| remove **adjudication** (report every red probe) | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| remove the **independent oracle** | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| referee sees only the clause, not the whole specification | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| remove the **ambiguity gate** (probe under-determined obligations) | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| remove **archetype memory** | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| **add** the implementation's docstrings to the surface map (removed experiment) | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |
| remove **property-based probes** | 1/9 (ref 1/9) | +0 pp | 0/6 (ref 0/6) | +0 pp | 15 |

**Every row is a null result, and that is the finding rather than a disappointment.** These ablations remove components from a configuration that detects 1 of 9 held-out defects. There is no headroom to lose: a component cannot be shown to contribute when the system it is removed from is already at the floor. `ref` is full Blindspot restricted to exactly the cases each ablation saw, so the columns compare like with like.

The component that *did* earn its place — the Oracle — was measured a different way, by bolting it onto a system that does detect things. That is the `agent_plus_oracle` row in the results table above.
<!-- END:ablations -->

The full story of how the system got here — including the experiments that were removed —
is in the **[Improvement Changelog](CHANGELOG.md)**.

### What it costs

<!-- BEGIN:cost -->
| System | Model calls | Content tokens in/out | Est. USD | Wall clock |
|---|---|---|---|---|
| Baseline A: one direct prompt | 35 | 75,021 / 38,791 | $0.81 | 1s |
| Baseline B: general agent with tools | 156 | 403,331 / 58,619 | $2.09 | 4s |
| Blindspot | 396 | 518,662 / 129,410 | $3.50 | 704s |
| Blindspot (search-first probes) | 417 | 632,981 / 146,153 | $4.07 | 897s |
| General agent + spec-anchored Oracle | 337 | 853,889 / 118,973 | $4.35 | 77s |

Totals across the whole test split. Tokens are **content** tokens (the actual prompt and completion text); see [REPRODUCE.md](REPRODUCE.md#cost) for why the transport's own overhead is reported separately. **The wall-clock column is from the offline replay**, so it measures sandbox execution rather than model latency — which is why a system that makes more calls can show less of it. Live wall clock is dominated by the model and is roughly proportional to the call count.
<!-- END:cost -->

---

## 6. Install and run

```bash
git clone <this repo> && cd blindspot
python -m pip install -e .          # Python 3.11+; no compiler, no Docker
make doctor                          # environment check
make reproduce                       # the headline result, offline, ~1 min
```

Then see it work on a real case:

```bash
make demo                            # one audit end to end, narrated, offline
make trace                           # render the trajectories to a single HTML file
```

Audit your own code:

```bash
blindspot audit --spec path/to/SPEC.md --impl path/to/impl.py --format pr
blindspot decide <task_id>           # answer the questions the spec leaves open
```

Full clean-environment walkthrough, versions, runtimes and cost:
**[REPRODUCE.md](REPRODUCE.md)**.

---

## 7. Repository map

```
src/blindspot/
  agents/         cartographer · surface · adversary · referee · oracle · adjudicate
                  · memory · pipeline
  prompts/        every agent instruction, as reviewable Markdown
  llm/            provider layer + content-addressed cassette record/replay
  sandbox/        isolated, deterministic execution of model-written code
  eval/           grader (no model in the scoring path) · stats · report · runner
  forge/          corpus construction + differential fuzzing
  baselines/      the two baselines the brief asks for
  trace/          trajectory recording + the self-contained HTML viewer
spectrap/
  tasks/          14 tickets: SPEC.md, hidden reference, generators, standard-traceable
                  selftest, independent crosscheck oracle, metadata
  cases/          forged cases: model-written impl + its own tests + label + witness
  SPLIT.yaml      the frozen dev/test split, with its seed and procedure
cassettes/        every recorded model call — this is what makes replay free
results/          per_case.csv · summary.json · RESULTS.md · integrity reports
trajectories/     agent trajectories (JSONL) + viewer.html
decisions/        human answers to questions specifications leave open
scripts/          verify_corpus · label_spec_visible · freeze_corpus · run_crosscheck
                  · compare_results · triage_audit · check_docs · demo · update_readme
```

---

## 8. Limitations

Stated plainly, because a system that hides them is not one you should trust with a review.

- **The benchmark measures the wrong thing, and this is now measured rather than suspected.**
  `has_defect` is assigned by differential fuzzing against a reference, so it means "differs
  from the reference", not "violates the specification". Only 3 of 16 buggy cases are
  specification violations (`spec_visible` in each `meta.yaml`, computed by
  `scripts/label_spec_visible.py`). Every detection rate below should be read with that in
  mind, and the spec-visible subset is reported separately — on a subset of **2 held-out
  cases**, which supports no conclusion at all beyond "we know which two".
- **The central hypothesis was refuted.** Blindspot detects 1 of 9 held-out defects against
  the code-reading agent's 5. Two attempts to repair it in place failed, one of them
  rejected on the dev split before it ever reached test. The configuration that *does* beat
  the baseline — `agent_plus_oracle` — abandons the original idea's premise: it lets a
  code-reading agent choose the inputs and applies the barrier only to the oracle.

<!-- BEGIN:limits_n -->
- **Small n.** 9 held-out buggy cases carrying **4 distinct defects**, and 26 clean ones. The defect count is the one that bounds the evidence: several cases can be different implementations of the same misreading. The power ceiling is stated in §4; nothing here is a significance claim.
<!-- END:limits_n -->
- **Single-function, pure, deterministic tasks.** No I/O, no concurrency, no repository-scale
  change. Blindspot has not been shown to work on a real pull request touching many files.
- **The barrier needs a specification.** If the ticket is a one-line Slack message, there are
  no obligations to derive, and Blindspot degrades to a slower, more expensive baseline.
- **The reference is the oracle.** Soundness is defined relative to a hand-written reference.
  A defect the reference shares is invisible — which is exactly why every reference is
  independently cross-checked (§3), and why that cross-check is shipped rather than
  described.
- **The sandbox contains accidents, not adversaries.** It stops hangs, runaway memory,
  network access and stray writes, and it runs as the calling user. **No container mode is
  shipped.** That is fine for code the operator just asked a model to write and would not be
  fine for code from an untrusted source.
- **Everything ran on one model family.** The corpus was forged by two models
  (Claude Haiku 4.5 for 35 cases, Sonnet for 18), but every system under evaluation used the
  same family, and **no cross-model generalisation run was done**. Whether these results
  transfer to code written by a different model family is untested, and the provider layer
  supports it (`--provider openai`) if someone wants to check.
- **The `agent_plus_oracle` result rests on one case flip.** 6/9 against 5/9 is a single
  case out of nine, on a corpus with 4 distinct defects. It is directional evidence with a
  mechanism attached, not a significance claim, and the mechanism — removing an unsound test
  that was disqualifying a sound one — is visible in a single trajectory.
- **`self_tests` scores 0 by construction** on buggy cases. That is the point being made,
  but it means it is a floor, not a competitor.

---

## 9. Hot take

**If you build an agent evaluation by diffing a candidate against a reference
implementation, you are grading mimicry and calling it correctness.**

This is the lesson that cost the most to learn, and it is the one that generalises past
this project. Differential fuzzing is the obvious way to label a defect corpus without
hand-writing every test: generate a candidate, fuzz it against a known-good implementation,
and call any disagreement a bug. It is cheap, it is mechanical, and it feels rigorous.

It is measurably not. A specification determines *some* of a function's behaviour and
leaves the rest open, and two correct implementations differ freely in the gap. Running
each task's authoritative, standard-traced suite against every case this corpus labelled
buggy shows **13 of 16 violate nothing the specification actually says**. The label was
never "wrong"; it was answering a different question than the one it appeared to answer.

The consequence for the systems under test is the part worth internalising. On a benchmark
like this, **the way to score well is to guess what the reference author would have
written** — which is what an agent that reads the code and pattern-matches to plausible
behaviour does, and it collected 4 of its 5 detections that way. A verifier that accuses
only when the specification determines the answer stays silent and scores zero. The
benchmark ranks them in exactly the wrong order, for a reason invisible in its own headline
metric.

**How to check whether your own evaluation has this problem:** take the cases your
benchmark calls defects, and run whatever you consider the authoritative statement of
required behaviour against them. Anything that passes is a difference, not a defect. If
that is most of your corpus, your leaderboard is measuring oracle-mimicry.

### The runner-up: "independence" is two properties, not one

The original thesis was that test independence is an information-flow property — separate
the *information*, not the org chart. Half of that survives contact with the data, and it
is the half nobody separates:

- **Independence of what you expect** — the oracle. This wants *less* information. Show the
  agent the implementation and it will rationalise whatever the implementation does; the
  barrier here is real and it works. Blindspot emitted **zero unsound claims and zero false
  alarms across 26 clean cases**, against 5–11 for every baseline. It never once cried wolf.
- **Independence of where you look** — the search. This wants *more* information, and the
  barrier is actively harmful. Reading the code is how you learn which boundary is
  hard-coded and which input shape is unhandled.

Blindspot applied one barrier to both and paid for it. Three separate attempts to recover
the search half — letting the adversary read the code for inputs only, making it *search*
the domain with `hypothesis` instead of guessing a point (which moved property-based probes
from 8% to 50% of its output), and bolting the specification-anchored oracle onto the
strong baseline — are all in the [changelog](CHANGELOG.md), and **none of them worked**.
Two were rejected on the dev split and never promoted to test.

The design that follows from this, and what I would build next: **use a code-reading agent
to propose inputs, and a specification-anchored oracle that never sees the proposal to
decide what the answer should be.** Blindspot has both halves; it just wired the barrier
across the wrong one.

---

## 10. What existed before this competition

Everything in this repository was written for this challenge. The dependencies are
`pydantic`, `PyYAML`, `rich`, `Jinja2`, `hypothesis` and `pytest` — all used as published,
under their own licences. No pre-existing agent framework was used; the orchestration,
cassette layer, sandbox, forge, grader and statistics are original to this submission.

Model access is via the Claude Code CLI in headless mode (a Claude subscription), or any
Anthropic/OpenAI-compatible API key. **Reproducing the published results requires
neither** — see [REPRODUCE.md](REPRODUCE.md).

### Tool disclosure

The brief requires coding-agent use and its disclosure.

- **Claude Code (Claude Opus 5)** was used to write this repository — the source, the
  specifications, the tests and the documentation — driven interactively across the
  competition window. The work was directed, reviewed and corrected throughout; several of
  the changelog entries are bugs found by measurement rather than by reading, which is the
  honest characterisation of how it went.
- **Claude Code in headless mode (`claude --print`, Haiku 4.5 and Sonnet)** is the model
  backend the *system itself* calls at runtime, for every agent stage and for the forge.
  Those calls are the ones recorded in `cassettes/` and rendered in `trajectories/`.
- No other AI tool, agent framework or code-generation service was used. No code was copied
  from another project.

The distinction matters for reading the trajectories: they are the transcripts of the
**system under evaluation**, not of the assistant that helped build it.

Licensed under Apache-2.0. See [LICENSE](LICENSE).
