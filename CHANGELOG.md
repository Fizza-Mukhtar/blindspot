# Improvement Changelog

How Blindspot got from a single prompt to the system in [README.md](README.md), what each
change was worth, and the things that were tried and cut.

Every row's evidence is a file in this repository. Nothing here is recalled from memory;
where a number appears, the command that produced it is named.

**Reading order.** Iterations 1–3 build the measuring instrument, because a system with no
instrument cannot be improved, only admired. Iterations 4–6 are the corpus discovering its
own bugs. Iterations 7–12 are the agent. Iterations 13–21 are what the first live runs broke, and 22–32 are what the
held-out split broke — including the benchmark itself,
which is where most of the real learning is. The removed experiments are at the end,
with what they taught.

---

## The summary table

| Stage | What was tried, and why | Evidence | Decision / learning |
|---|---|---|---|
| **Baseline** | One direct prompt: spec + implementation + *"write tests that find bugs."* One call, no execution. | `results/per_case.csv`, system `baseline_direct` | Established the floor. |
| **Baseline 2** | A general-purpose ReAct agent with a sandbox and six rounds — the setup most people would actually reach for. It sees the implementation body, which Blindspot never does. | system `baseline_agent` | Kept as the honest bar. Beating only a naive prompt would prove nothing. |
| **Iteration 1** | Built the grader *before* the agent, as a pure execution predicate. | `tests/test_grader.py`, 10 tests | Kept. Found immediately that a "fails on the candidate" rule scores `assert False` at 100%. |
| **Iteration 2** | Content-addressed record/replay for every model call. | `make reproduce`, `cassettes/` | Kept. Turned reproduction from a promise into a one-minute offline command. |
| **Iteration 3** | Split each system's output into one module per test so the grader can give per-test verdicts. First attempt was a textual split on `def test_`. | `tests/test_splitting.py`, 7 tests | **Revised.** The textual split severed `@pytest.mark.parametrize` decorators, turning parameters into missing fixtures. It manufactured four bogus "unsound" verdicts on the first real case. Replaced with an `ast` split. |
| **Iteration 4** | Audited the corpus against itself: every reference re-derived independently from the standard by an author who never saw it, then differentially fuzzed. | `make crosscheck`, `results/crosscheck.json` | **Found 4 real bugs in our own ground truth**, all the same bug class, in 4 references by 4 different authors. Fixed, and encoded as a permanent guard in `tests/test_reference_hygiene.py`. |
| **Iteration 5** | Measured the corpus's defect yield on the detailed ticket rendition. | `results/forge_report.json` | **The corpus was too easy.** Both a large and a small model implemented the enumerated specifications correctly almost every time. Led directly to iteration 6. |
| **Iteration 6** | Added a second ticket rendition — the same requirements written as a working engineer writes them, prose instead of numbered rules, the tricky clause present but unsignposted. | `spectrap/tasks/*/SPEC.terse.md`, `docs/SPEC_FAIRNESS.md` | Kept, as a **second experimental condition**, not a replacement. Ticket style turns out to be a variable worth reporting in its own right. |
| **Iteration 7** | The information barrier: derive obligations from the specification with the implementation withheld. | ablation `abl_no_barrier` | Kept — see the ablation table. This is the project's central claim. |
| **Iteration 8** | Mechanical verbatim-quote verification on every obligation. | `tests/test_cassette_and_barrier.py::test_verified_quotes_survive_and_invented_ones_do_not` | Kept. Cheap, deterministic, and it makes a hallucinated requirement structurally unable to become an accusation. |
| **Iteration 9** | Barrier **attestation**: hash the spec-reader's context and assert no implementation line appears in it. | `barrier_attest` events in `trajectories/`, `make demo` | Kept. An architecture diagram is not an enforcement mechanism. |
| **Iteration 10** | The ambiguity gate: withhold obligations resting on questions the specification does not settle, and escalate them to a human. | ablation `abl_no_gate`; `blindspot decide` | Kept — see the ablation table. |
| **Iteration 11** | The referee: adjudicate every red probe with strictly less context than the probe had. | ablation `abl_no_referee` | Kept — see the ablation table. |
| **Iteration 12** | Archetype memory learned from the dev split only, with a mechanical leakage check. | ablation `abl_no_memory`; `blindspot learn` | See the ablation table; kept/revised on the evidence there. |
| **Iteration 13** | Ran the whole pipeline live for the first time, on one real case. | `results/smoke/records.json` | **Blindspot emitted zero tests on every case.** The barrier attestation was firing on the function signature — which the ticket itself publishes. A guard strict enough to be meaningless. Fixed and given a positive control. |
| **Iteration 14** | Made recording replay-first, so an interrupted live run resumes instead of re-buying every call. | `tests/test_cassette_and_barrier.py::test_an_interrupted_recording_resumes_from_where_it_stopped` | Kept. The first long run died on a usage limit and lost everything; this turned a 4-hour outage into a restart. |
| **Iteration 15** | Capped in-flight model calls process-wide. | `tests/test_cassette_and_barrier.py::test_the_inflight_limit_bounds_nested_thread_pools` | Kept. The evaluation nests thread pools, so `--concurrency 6` was really up to 36 subprocesses; single calls were taking minutes. Throughput is now one number, not the product of two. |
| **Iteration 16** | Fed the referee *what the test asserted*, extracted with `ast`. | `tests/test_grader.py::test_a_raised_exception_does_not_report_expected_equal_to_actual` | Kept. When a probe failed by raising, the captured output held only the exception, so the referee was comparing an observation against nothing — and reports read "expected X, produced X". |
| **Iteration 17** | Gave the referee the **whole specification**, not just the clause the obligation came from. | cassette `41f792b3…`, ablation `abl_clause_only_referee` | **Kept, but it did not fix the problem.** The referee upheld the same false accusation with the entire document in front of it. Being shown the right words was not enough — it had already been told what the answer was supposed to be. Led directly to iteration 18. |
| **Iteration 18** | The **Oracle**: an independent reading that sees the specification and one call, and never sees the claim, the clause, the probe or the implementation. Its answer is compared to the probe's assertion **mechanically** (`ast.literal_eval`), with no model adjudicating. | ablation `abl_no_oracle`; `trajectories/` `oracle.second_opinion` events | Kept. On the case that motivated it the oracle predicted `raises UnsatisfiableRange`, contradicted the probe's `[(0, 0)]`, and withdrew the finding. It can only ever *remove* an accusation, never create one. |
| **Iteration 19** | Checked that the strong baseline was actually running. | `results/agent_smoke/per_case.csv` | **It was not.** `baseline_agent` had been scoring 0 on every case because the CLI was invoked with a one-turn budget and the model spent that turn reaching for a tool. Fixed; it now detects defects Blindspot misses. A baseline that silently scores zero is not a baseline, it is a flattering bug. |
| **Iteration 20** | Asked the forge for twelve implementations per ticket instead of four. | `tests/test_cassette_and_barrier.py::test_a_caller_supplied_nonce_separates_repeat_samples` | **It had been silently returning four.** Prompts go out at temperature 0 and the style list had four entries, so variants 4-11 were byte-identical requests that hit their own cassette and replayed the first implementation. `--variants 12` meant four. Fixed with a caller-supplied nonce *and* a longer style list — the cache key was only half the bug; identical prompts return identical code however you key them. |
| **Iteration 21** | Counted *distinct defects* rather than cases. | `spectrap/CORPUS.lock`, `results/per_case.csv` column `trap_id` | The forge writes several implementations per ticket and more than one can fail on the same witness: 16 buggy cases carried 6 distinct defects. Reporting those as 16 independent observations would have overstated the evidence roughly threefold. Intervals are now also computed by resampling defects, and the headline states both counts. |
| **Iteration 22** | Ran the pre-registered configuration on the held-out split for the first time. | `results/per_case.csv`, `results/summary.json` | **The central claim failed.** Blindspot detected **1 of 9** held-out defects against the general agent's **6 of 9**. It was not the adjudication chain over-filtering: the Oracle withdrew exactly one finding all run. Of ten probes on a missed case, **ten passed** — working from the specification alone, the adversary never guessed the input that breaks the code. What the barrier *did* buy was precision: **4% false alarms against 35-38%**. |
| **Iteration 23** | Separated the barrier on the **oracle** from the barrier on the **search**: the adversary may read the implementation to decide *where to aim*, while the obligation it tests against still comes from the barrier-attested, spec-only ledger, and the Referee and Oracle never see the code. | system `blindspot_targeted`; dev split | **Dropped, and the reason matters more than the idea.** Dev moved 0/7 → 2/7, and then the identical configuration re-run on dev gave 0/7. The variance was real and was in the *measurement*, not the system (iterations 24 and 30). The configuration is implemented and registered but is **not in the reported sweep**: promoting on a dev result that does not reproduce is the mistake pre-registration exists to prevent. The idea itself survived, in `agent_plus_oracle`. |
| **Iteration 24** | Re-ran one configuration twice and compared. | `tests/test_grader.py::test_a_timeout_is_retried_with_more_headroom` | **The two runs disagreed.** The grader treated a sandbox timeout as an *observation*: a counterexample whose first execution timed out scored as no detection, and one whose determinism re-run timed out was branded flaky and discarded. With nine sandboxes running at once, that made the headline numbers partly a function of how loaded the machine was. A timeout is now inconclusive — retried with more headroom, and never counted as a disagreement. |
| **Iteration 25** | Told the adversary to **search** the input domain with a `hypothesis` property rather than guess a single input — measurement had shown 89% of its probes were one hand-picked value and only 8% searched at all. | `results/dev_search/summary.json`; system `blindspot_search` | **Rejected on dev, never promoted to test.** The directive worked — property-based probes went from 8% to 50% of output — and detection did not move: 0/7, same as guessing. Random search from the specification does not reach `bytes= ,0-1` any more reliably than a guess does. |
| **Iteration 26** | Asked whether the corpus's "defects" are actually specification violations, by executing each task's authoritative standard-traced suite against every buggy implementation. | `scripts/label_spec_visible.py`; `spec_visible` in every `meta.yaml` and in `results/per_case.csv` | **13 of 16 violate nothing the specification says.** They differ from the reference only where it is silent. `has_defect` had been assigned by differential fuzzing, which answers "does this differ from the reference", not "does this violate the spec". **4 of the 5 detections that made the baseline look good are on those cases.** This is the project's main finding and it is now a first-class, mechanically-computed label rather than a footnote. |
| **Iteration 27** | Noticed that `agent_plus_oracle` was scoring *identically* to the baseline it wraps — same detections, same false alarms, same cases — and went looking for why. | `results/records.json`, field `error` | **The Oracle was crashing on 14 of 35 cases** and the pipeline was falling back to passing the agent's tests through unfiltered. Asked to work a call out "step by step", the model narrated until it hit the token limit and the reply contained no parsable JSON at all. Fixed by keeping the working *out* of the output and raising the ceiling. |
| **Iteration 28** | Added an **errored-runs column** to the results table. | `README.md` §5 | A stage that crashes and falls back to passing its input through is indistinguishable, in every other column, from a stage that ran and changed nothing. Iteration 27 was only caught by an unrelated hunch; nothing in the report would have surfaced it. **Fail-open plus an aggregate metric equals a silent lie**, and the fix is to make the failure a column rather than a comment. |
| **Iteration 29** | Chased the last of the run-to-run variance between two *offline replays of identical cassettes*. | `tests/test_sandbox.py::test_a_locked_trajectory_file_does_not_kill_the_run` | Three evaluation runs were dying on `PermissionError` — from the **trajectory writer**, because the repository sits in a synced folder and the sync client held the file open for a moment. A logger was killing the runs it was supposed to observe, and it showed up as unexplained variance in the results. Trajectory writes now retry briefly and then drop the line, counting the loss. **Observability must not be able to fail the thing it observes.** |
| **Iteration 30** | Ran `make reproduce` against the frozen results and read the diff instead of the summary. | `tests/test_cassette_and_barrier.py::test_concurrent_runs_do_not_renumber_each_others_cassettes` | **One run of 330 did not reproduce**, and the cause was in the reproducibility layer itself: the cassette store kept a *single global* occurrence counter and cleared it at the start of each run, while the sweep executes runs concurrently. One job's reset renumbered another job's in-flight lookups, so a replay could take a different path from the run it was replaying. Counters are now scoped by run id. **A reproduction check that only compares summaries would never have caught this** — it compares the per-case table for exactly this reason. |
| **Final** | `agent_plus_oracle`: a code-reading agent chooses the inputs, and a specification-anchored Oracle that never sees the accusation adjudicates every red test. | `results/summary.json`; `trajectories/agent_plus_oracle--discount_stacking__v12.jsonl` | **The only configuration that beats the fair baseline.** 6/9 against 5/9 at an identical false-alarm rate, and 2/2 against 1/2 on the cases that are genuine specification violations. The barrier belongs on the oracle, never on the search — which is the opposite of where this project started. |
| **Iteration 31** | Ran the reproduction check again after fixing iteration 30, and read the diff again. | `tests/test_sandbox.py::test_a_slow_probe_is_retried_before_being_called_a_timeout` | **One run in 330 still differed.** The grader had been taught that a timeout is inconclusive (iteration 24); the *adversary's* probe execution had not. A property-based probe that timed out under load looked like a broken probe, so the agent spent repair attempts on it and took a different path — two replays of identical cassettes, one emitting a test the other did not. The retry now lives in `run_probe`, where every caller gets it. |
| **Iteration 32** | Watched somebody run `make reproduce-quick` from PowerShell instead of git-bash. | `Makefile`, targets `reproduce` and `reproduce-quick` | **It failed immediately.** Two recipes used `BLINDSPOT_PROVIDER=replay python ...`, which is POSIX shell syntax; GNU make on Windows picks `cmd.exe` outside git-bash, where that is a syntax error. Every offline run had been launched from git-bash, so the one command the whole submission points at was broken on the platform it was developed on. Replaced with the `--provider replay` flag, which no shell has an opinion about. **A reproduction path is only as portable as the shell you last tried it in.** |
| **Removed** | Letting the adversary see the implementation's **docstrings**. | ablation `abl_docstrings` | See "Experiments removed" below. |
| **Removed** | Re-rolling probes that came back green until one turned red. | — | Removed on principle *and* on evidence: it is a false-alarm generator. See below. |
| **Final** | The combination in `README.md` §5. | `results/summary.json` | The largest single contributor is named in the ablation table. |

---

## The evidence, in detail

### Iteration 1 — build the instrument before the thing it measures

The first version of the scoring rule was "the system found the bug if one of its tests
fails on the implementation." Writing the test for that rule is what killed it:

```python
def test_assert_false_scores_zero(synthetic_case):
    grade = grade_case(synthetic_case, system="t", tests=[ASSERT_FALSE], repeats=1)
    assert grade.detected is False
```

`assert False` fails on every implementation ever written, so under the first rule it
scored 100%. The fix is the second conjunct — *every* emitted test must also **pass** on a
hidden reference — which turns "red" into "red here, green on correct code", i.e. a sound
counterexample.

This is the reason the harness was built first. Had the agent come first, it would have
been tuned against a rule that could be satisfied by a constant.

### Iteration 3 — a harness bug that looked like a finding

The first real evaluation reported that 4 of a model's 18 self-written tests *rejected the
correct reference implementation*. That is a striking claim, and exactly the kind this
project exists to make — so it got checked before it got written down.

It was false. The suite-splitting code cut on `def test_` boundaries, which left
`@pytest.mark.parametrize` decorators attached to the previous chunk. The parameters became
undeclared fixtures and the tests *errored*; the grader counted the errors as the suite
being wrong.

**The learning, which generalises well beyond this project:** a measurement bug and a
finding are indistinguishable from the summary statistic. The only defence is to look at
the individual case before believing the aggregate. `tests/test_splitting.py` now asserts
that every produced module actually runs.

### Iteration 4 — the corpus had the disease it was built to diagnose

The 14 reference implementations and their standard-traceable tests were written together,
by the same author, per task. That is precisely the correlated-authorship risk the whole
project is about — so the corpus was subjected to its own treatment: each reference was
independently re-derived from `SPEC.md` and the cited standard by an author forbidden from
reading it, and the two were differentially fuzzed against each other.

Across ~40,000 compared inputs, 13 of 14 agreed. The disagreements found **four real
defects in the ground truth**, and every one was the same bug:

```python
re.compile(r"^([0-9]+):([0-9]+)$")     # accepts "200:9\n"
re.compile(r"^-?\d+(?:\.\d+)?$")       # accepts "5.00\n", and Arabic-Indic numerals
```

Python's `$` also matches immediately before a single trailing newline, and Python's `\d`
matches every Unicode decimal digit — which `int()` then happily accepts.

The detail that makes this worth reporting: the four references were written by four
different authors working independently on four unrelated tasks, and **one of those authors
had explicitly reasoned about `int()` accepting non-ASCII digits and chosen `[0-9]` for
that reason — and still wrote `$`.** Deliberate care about the adjacent issue did not
transfer.

The correlated blind spot is not a property of one model instance. It is a property of the
training distribution, and it does not care that you separated the authors.

Fixed in all four; `tests/test_reference_hygiene.py` now fails the build if any reference
regresses, across 42 parametrised checks.

### Iteration 5 → 6 — the corpus was too easy, and that was itself a finding

With the detailed ticket rendition, the forge produced almost no defects: a large model
implemented the enumerated specifications correctly nearly every time, and a small one was
not much worse.

The specifications were the problem. Written to be *fair*, they had become **requirements
documents**: every tricky rule enumerated under its own numbered heading. A model reading
"numeric identifiers always have lower precedence than non-numeric identifiers" as item
11.4.3 of a bulleted list simply implements it. The clause was not a trap, because it was
signposted.

Rather than weaken the specifications — which would have made detection unfair, since an
undetermined requirement cannot be violated — a **second rendition** was added: the same
requirements, written the way an engineer writes a ticket. Prose, not lists. The tricky
clause mid-paragraph, in the same register as everything around it. Normative points
carried by reference to the cited standard where the standard settles them.

Fairness is audited rather than assumed: for every terse ticket, each assertion in
`selftest.py` is traced to the sentence that determines it, recorded in
`docs/SPEC_FAIRNESS.md`. A requirement may be *compressed*; it may never be *removed*.

Both renditions are kept and reported separately. Ticket style is a variable a team can
actually act on.

---

## What each component was worth

**Almost nothing measurable, and the reason is worth more than the table.** Every ablation
below removes one component from a configuration that detects 1 of 9 held-out defects.
There is no headroom to lose: a component cannot be shown to contribute when the system it
is removed from is already at the floor. The table is reported in full because it is the
evidence for that statement, not because it ranks the components.

This is a real limitation of the experiment, not a presentational one. Ablations are only
informative on a system that works, and the honest reading of these rows is *"the
pre-registered configuration failed, so its parts could not be priced"*. The component that
*did* demonstrably earn its place is the Oracle, and it was measured a different way — by
bolting it onto a system that does detect things (`agent_plus_oracle` in the results table),
where its single withdrawal converted a miss into a detection without adding a false alarm.

<!-- BEGIN:changelog_ablations -->
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
<!-- END:changelog_ablations -->

---

## Experiments removed

### Removed: letting the adversary see the implementation's docstrings

**Why it was tried.** The surface map deliberately gives the adversary signatures but not
behaviour. Docstrings sit exactly on that line: they are not code, they describe intent,
and withholding them felt like excessive purity.

**Why it was removed.** A docstring is author prose, written by the same process that wrote
the misreading. `"""Sort tags."""` on a function that sorts them lexically is not neutral
information — it is a confident, wrong summary, and it is *more* persuasive than the code
because it reads like a specification.

The ablation `abl_docstrings` keeps everything else fixed and adds only the docstrings to
the surface map. **It measured nothing**, along with every other ablation, for the reason
given above: the configuration it modifies detects one defect, so there was nothing for a
docstring leak to cost. The argument for removing docstrings therefore rests on the
principle below and *not* on evidence from this run — which is why it is stated as a
principle.

**The generalisation:** when deciding what an auditing agent may see, the test is not "is
this code?" but *"was this produced by the process being audited?"* Comments, docstrings,
commit messages, PR descriptions and the original prompt all fail that test.

### Removed: re-rolling green probes until one turned red

**Why it was tried.** An obligation probed once and found satisfied might just have been
probed badly. Sampling a second and third probe is the obvious way to raise detection.

**Why it was removed.** It is a false-alarm generator with extra steps. Sampling until a
test turns red conditions the output on redness, which is precisely how a wrong accusation
gets manufactured — and the more attempts allowed, the more confidently wrong the result.
The published literature agrees that spec-checking models already over-flag correct code
([arXiv:2508.12358](https://arxiv.org/abs/2508.12358)).

The rule that replaced it is in `adversary.py` and is one line of policy: **`PASS` is
recorded and not retried; only `ERROR` is retried, and only because an unrunnable probe is
not evidence either way.** Retrying a *broken* probe is repair. Retrying a *green* probe is
p-hacking.

### Removed: an LLM judge in the scoring path

**Why it was tried.** It is the standard move, and it is far easier than maintaining 14
reference implementations and a differential fuzzer.

**Why it was removed.** Before it was ever built. The judges of this competition evaluate
AI agents for a living, and a number produced by a model grading its own family's output is
not evidence. Every metric reported here is an execution predicate. The referee assigns a
triage *category* and **no reported number is a function of that category** — which is a
claim worth checking rather than trusting, so `scripts/triage_audit.py` writes
`results/triage_audit.csv`: every finding that reached the reader, its referee outcome, and
the grader's independent execution verdict beside it. Where the two disagree, the grader is
right by construction, and the row is a false accusation that survived adjudication.

---

## The main failure mode

**Silence.** The system declines to accuse, and then declines almost every time.

This is not the failure mode the design anticipated. The whole architecture — the
asymmetric referee, the ambiguity gate, the independent oracle, the ∀-clause in the metric
— was built against *the confident wrong accusation*, on the reasoning that a false
accusation costs a reader's trust in every other finding while a missed defect costs one
finding. That reasoning is still sound, and the defences work: **0 unsound claims and 1
false alarm across 26 clean implementations**, the best precision of any system measured.

They work so well that nothing survives them. On the held-out split the pre-registered
configuration detects **1 of 9** defects. Every guard is individually defensible and
collectively they add up to a system whose answer is always "I cannot show that this is
wrong", which is worth nothing to the reviewer who has to decide whether to merge.

Three things had to be true at once for this to happen, and only the first was foreseen:

1. **Precision was bought with recall, and the price was not measured until the end.**
   Each guard was justified in isolation. Nothing measured their *product* until the
   held-out run, by which point there were five of them.
2. **The barrier blinded the search, not just the oracle.** An adversary that never sees
   the implementation has to guess which of billions of inputs matters. Ten probes on a
   missed case, ten passes. Telling it to *search* with `hypothesis` instead of guessing
   moved property-based probes from 8% of its output to 50% and changed detection by
   nothing at all.
3. **The benchmark rewarded a behaviour the system was built to refuse.** 13 of 16 of its
   defects violate nothing the specification states, and a verifier that accuses only on
   determined behaviour is *correct* to stay silent on them — while scoring zero for it.

**The generalisable lesson.** A verifier's failure mode flips depending on which side of
the precision/recall trade you defended, and defending one side is not free. Anyone
building an auditing agent should measure both from the first day, on held-out data, and
should be suspicious of a component list where every item was justified on its own. The
question to ask of each new guard is not "does this prevent a false accusation?" — it
always does — but "what is the running total of what my guards have cost me?"

---

## Hot take

**If you build an agent evaluation by diffing a candidate against a reference
implementation, you are grading mimicry and calling it correctness.**

Differential fuzzing is the obvious way to label a defect corpus without hand-writing every
test: generate a candidate, fuzz it against a known-good implementation, call any
disagreement a bug. Cheap, mechanical, feels rigorous. It is measurably not. A
specification determines *some* of a function's behaviour and leaves the rest open, and two
correct implementations differ freely in the gap. Running each task's authoritative,
standard-traced suite against every case this corpus labelled buggy shows **13 of 16
violate nothing the specification says**.

The consequence is the part worth internalising: on a benchmark like this, **the way to
score well is to guess what the reference author would have written.** A code-reading agent
that pattern-matches to plausible behaviour collected most of its detections that way. A
verifier that accuses only when the specification determines the answer stays silent and
scores zero. The benchmark ranks them in the wrong order for a reason invisible in its own
headline metric.

**The check:** take the cases your benchmark calls defects and run whatever you consider
the authoritative statement of required behaviour against them. Anything that passes is a
difference, not a defect. If that is most of your corpus, your leaderboard is measuring
oracle-mimicry.

### The runner-up, which is the actionable one

**"Independence" in verification is two properties, and they want opposite things.**

- **Independence of what you expect** — the oracle — wants *less* information. Show an
  agent the implementation and it will rationalise whatever the implementation does. This
  barrier is real and it works: 0 unsound claims and 1 false alarm across 26 clean
  implementations, the best precision measured.
- **Independence of where you look** — the search — wants *more*. Reading the code is how
  you learn which boundary is hard-coded and which input shape is unhandled.

Blindspot applied one barrier to both and detected nothing. The measured fix was to split
them: `agent_plus_oracle` lets a code-reading agent choose the inputs and puts a
specification-anchored oracle — which never sees the test, its author's reasoning, or the
implementation — in front of every accusation it makes. It beats the same agent unaided,
at identical false alarms, and it is the only system that caught both genuine
specification violations.

**The rule for the next agent:** put the information barrier on the oracle, never on the
search. And attest it in code, because a diagram is not an enforcement mechanism.

### The corollary iteration 4 paid for

**The blind spot is in the training distribution, not in the instance.** Four independent
authors wrote the same regex bug into four reference implementations. Separating the
authors does not decorrelate the errors — only changing what they can see does, and even
then only for the errors that come from what they read rather than from what they already
believed.
