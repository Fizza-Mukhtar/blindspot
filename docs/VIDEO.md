# Solution video — shot list

**Target 4:50. Hard cap 5:00.**

Everything on screen is reproducible offline and nothing is mocked for the camera. The
numbers you will read out are the ones in `results/summary.json`; if they have moved since
this was written, read the file, not this script.

## Before recording

```bash
make install
make trace          # builds trajectories/viewer.html
python scripts/demo.py --case full_jitter_backoff__v12   # ~100s; rehearse this shot once
```

`make reproduce` (~40 min) is worth running once beforehand to confirm the repository is in
the state you are filming, but it is not needed for any shot.

**If you are working inside OneDrive, Dropbox or iCloud, everything above is several times
slower** — the sandbox spawns thousands of short-lived processes and the sync client
contends for each one. Nothing is wrong; it is just slow.

Terminal at ~110×34, dark theme, font large enough to read at 720p. `python scripts/demo.py
--pace 0` removes the deliberate pauses if you would rather cut than wait.

**Tone.** This submission reports a refuted hypothesis and a benchmark-design finding. Say
that plainly and early — it is the strongest thing here, and hedging it reads worse than
the result does.

---

## 0:00 – 0:45 — The problem, shown not asserted

**On screen:** `spectrap/cases/discount_stacking__v11/self_tests.py`, then the terminal
running it green.

> "This is a test suite an AI wrote, for code the same AI wrote, from the same ticket,
> seconds earlier. It passes.
>
> It passes because both came from one reading of the specification. If that reading was
> wrong, the tests agree with the bug. On this benchmark, the model's own suite catches
> **zero of nine** defects in its own code — and separately, twenty-four of those
> self-written tests **reject a correct implementation**. Green CI here measures agreement
> between two model outputs, not correctness."

---

## 0:45 – 1:25 — The hypothesis, and the baseline it has to beat

**On screen:** the architecture diagram in `README.md` §2.

> "So: derive what the specification *demands* before you are allowed to see what the code
> *does*. A spec-only agent produces an obligation ledger — every clause quoted verbatim and
> checked by string match, so a hallucinated requirement cannot become an accusation. Only
> then does an adversary try to falsify the code against it.
>
> The bar is a general-purpose ReAct agent with a sandbox that **reads the implementation** —
> more information than Blindspot gets, not less. And all of it was pre-registered:
> endpoint, analysis plan, and the exact conditions that would refute it, committed before
> the held-out split was run."

**Show:** `PREREGISTRATION.md` §7, cursor on the refutation conditions.

---

## 1:25 – 2:25 — One realistic execution, end to end

**On screen:** run exactly this — it takes about 100 seconds, offline, no API key:

```bash
python scripts/demo.py --case full_jitter_backoff__v12
```

**Name the case honestly as you start it:** *"This is the one case in nine that Blindspot
catches — I'll come to the other eight in a moment."* Filming the single success without
saying so would be the one dishonest frame in the video, and the next shot is about to
admit it anyway.

(Plain `make demo` picks the first buggy case, where Blindspot finds nothing. That is the
representative outcome, not the useful one to film.)

Let it run. Narrate the stages as they appear:

> "The ticket. The implementation a model wrote from it. That model's own tests — green.
>
> The barrier attestation: the spec-reader's context is hashed and checked against the
> implementation source, and the run aborts if any line of the code appears in it. Not a
> diagram — an assertion, written into the trajectory.
>
> Obligations, each with a verbatim quote. A probe, run in a sandbox with no network and a
> timeout. And the part that decides whether a red test is a defect or a bad test: an
> independent reading of the specification that sees the call but never the accusation,
> compared mechanically with `ast.literal_eval`. No model adjudicates anything."

**End the shot on** the final panel, which the demo prints for you:

```
| the model's implementation | FAIL | the code violates the quoted clause       |
| the hidden reference       | PASS | the test is right about the specification |
```

> "Red on this code, green on a correct one. That conjunction is the entire scoring rule —
> and it is why `assert False`, which is red on everything, scores zero."

That is the grader's whole definition of a sound finding, and nothing in the scoring path
is a language model.

---

## 2:25 – 3:05 — The result: it does not work

**On screen:** `results/RESULTS.md`.

> "And it fails. Blindspot detects **one of nine** held-out defects. The general agent that
> reads the code gets five. Two of the pre-registered refutation conditions fired.
>
> What the barrier does buy is precision — **one false alarm across twenty-six clean
> implementations**, against nine and eleven for the two baselines. It almost never cries
> wolf. It also almost never finds anything."

*Do not soften this. The next two shots are what it bought.*

---

## 3:05 – 3:35 — Splitting the barrier in two

**On screen:** the `agent_plus_oracle` row.

> "The diagnosis: on a missed case, ten probes ran and ten passed. Working from the
> specification alone, it never guesses the input that breaks the code. The barrier that
> protects the *oracle* from the implementation's misreading also blinds the *search* — and
> those are separable.
>
> So: let a code-reading agent choose the inputs, and put the specification-anchored oracle
> in front of every accusation it makes. **Six of nine instead of five, at exactly the same
> false-alarm rate** — and it is the only system that catches both of the defects that are
> genuine specification violations.
>
> One withdrawal did that. The agent emitted a sound counterexample next to an unsound one,
> and under the grading rule a single unsound test throws the whole case away. The oracle
> never sees the test or the code — only the specification and the call — disagreed with the
> bad one, and the good one was credited. A stage that can only *remove* a test cannot
> invent a finding.

---

## 3:35 – 4:20 — The finding that outlives the project

**On screen:** run this live —

```bash
python scripts/label_spec_visible.py
```

> "Chasing that also turned up something about the benchmark rather than the agent.
>
> `has_defect` was assigned by differentially fuzzing each implementation against a
> reference — the standard cheap way to label a defect corpus. But that means *differs from
> the reference*, not *violates the specification*, and two correct implementations differ
> freely wherever the specification is silent.
>
> Run each task's authoritative, standard-traced suite against every case labelled buggy:
> **thirteen of sixteen violate nothing the specification states.** And most of the
> detections that make a code-reading agent look good are on exactly those cases.
>
> On a benchmark built this way, the way to score well is to guess what the reference author
> would have written. A verifier that accuses only when the specification determines the
> answer stays silent — and is right to. If you build agent evaluations by diffing against a
> reference, that is what you are grading."

---

## 4:20 – 4:50 — Changelog: what mattered, and what was removed

**On screen:** `CHANGELOG.md`, scrolling the summary table.

> "Twenty-nine iterations, each with the evidence that drove the next decision.
>
> **The change that contributed most was not to the agent — it was iteration 24, making the
> grader treat a sandbox timeout as inconclusive instead of as an observation.** Before that,
> the headline numbers moved depending on how loaded the machine was; a real counterexample
> whose re-run timed out was being discarded as flaky. No conclusion here was trustworthy
> until that was fixed.
>
> **One experiment I removed:** telling the adversary to *search* the input domain with
> `hypothesis` instead of guessing one input. It worked as an intervention — property-based
> probes went from eight percent of output to fifty — and detection did not move at all.
> Rejected on the dev split, never promoted to test.
>
> Everything you have seen replays offline from committed cassettes, with no API key and
> no network: `make reproduce`."

**Final frame:** `make reproduce` printing `REPRODUCED — N runs matched exactly`.
