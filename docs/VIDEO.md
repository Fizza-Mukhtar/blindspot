# Solution video — shot list

**Target 4:50. Hard cap 5:00.**

Nothing here is mocked for the camera. Every number you read out comes from
`results/summary.json`; if it has moved since this was written, trust the file.

---

## Part 0 — Set up once, before you press record

You need **two windows** and you will alt-tab between them:

| Window | What it is | How to open it |
|---|---|---|
| **A — Terminal** | PowerShell, in the project folder | you already have it |
| **B — Browser** | your GitHub repo page | <https://github.com/Fizza-Mukhtar/blindspot> |

GitHub renders the results tables properly, which is far easier to read on camera than raw
Markdown in a terminal. That is the only reason the browser is here.

**Run these two now. They are preparation, not shots:**

```bash
make trace
python scripts/demo.py --case full_jitter_backoff__v12
```

The second one is a **rehearsal** — watch it once so you know its pacing (about 100
seconds). You will run it *again* while recording, in Part 3. Running it twice is fine and
changes nothing: it replays from committed recordings.

> **If the project folder is inside OneDrive, Dropbox or iCloud, everything is several times
> slower.** Nothing is wrong. The sandbox spawns thousands of short-lived processes and the
> sync client contends for each one.

**To record:** press **Win + G** (Xbox Game Bar) → click record. Or use OBS.

**Tone.** This submission reports a hypothesis that failed. Say so early and plainly. The
result that *did* work lands harder after the admission than instead of it.

---

## Part 1 — 0:00–0:45 · The problem

**SHOW: Window A.** Run:

```bash
python -m pytest spectrap/cases/discount_stacking__v11/self_tests.py -q
```

It goes **green**.

> "This is a test suite an AI wrote, for code the same AI wrote, from the same ticket,
> seconds earlier. It passes.
>
> It passes because both came from one reading of the specification. If that reading was
> wrong, the tests agree with the bug. On this benchmark the model's own suite catches
> **zero of nine** defects in its own code — and twenty-four of those self-written tests
> **reject a correct implementation**. Green CI here measures agreement between two model
> outputs, not correctness."

---

## Part 2 — 0:45–1:25 · The idea, and the bar it has to clear

**SHOW: Window B.** Scroll the README down to the diagram under **"2. The hypothesis"**.

> "So: derive what the specification *demands* before you are allowed to see what the code
> *does*. A spec-only agent produces an obligation ledger — every clause quoted verbatim and
> checked by string match, so a hallucinated requirement can never become an accusation.
> Only then does an adversary try to falsify the code against it.
>
> The bar is a general-purpose agent with a sandbox that **reads the implementation** — more
> information than my system gets, not less."

**SHOW: still Window B.** Click `PREREGISTRATION.md` in the file list, scroll to **§7**.

> "And it was pre-registered: the endpoint, the analysis plan, and the exact conditions that
> would prove me wrong — written before the held-out split was ever run."

---

## Part 3 — 1:25–2:25 · One real execution

**SHOW: Window A.** Run:

```bash
python scripts/demo.py --case full_jitter_backoff__v12
```

**Say this as it starts** — it matters:

> "This is the one case in nine that my system actually catches. I'll come to the other
> eight in a moment."

Then narrate as the stages scroll past:

> "The ticket. The implementation a model wrote from it. That model's own tests — green.
>
> The barrier attestation: the spec-reader's context is hashed and checked against the
> implementation source, and the run aborts if any line of the code appears in it. Not a
> diagram — an assertion, written into the trajectory.
>
> Obligations, each with a verbatim quote from the ticket. Then a probe, executed in a
> sandbox with no network."

**END THE SHOT ON** the final panel, which the demo prints for you:

```
| the model's implementation | FAIL | the code violates the quoted clause       |
| the hidden reference       | PASS | the test is right about the specification |
```

> "Red on this code, green on a correct one. That conjunction is the entire scoring rule —
> and it is why `assert False`, which is red on everything, scores zero. There is no
> language model anywhere in that judgement."

---

## Part 4 — 2:25–3:05 · It does not work

**SHOW: Window B.** On the README, scroll to **"5. Results"** — the big table.

Point at the **Blindspot (pre-registered)** row.

> "And it fails. One of nine held-out defects, against the code-reading agent's five. Two of
> the pre-registered refutation conditions fired.
>
> What the barrier does buy is precision — **one false alarm in twenty-six** clean
> implementations, against nine and eleven for the two baselines. It almost never cries
> wolf. It also almost never finds anything."

*Do not soften this. The next shot is what it bought.*

---

## Part 5 — 3:05–3:40 · Splitting the barrier in two

**SHOW: the same table, same screen.** Point at the row labelled
**"Agent + spec-anchored Oracle"** — the bottom one, in bold.

> "The diagnosis: on a missed case, ten probes ran and ten passed. Working from the
> specification alone, it never guesses the input that breaks the code. The barrier that
> protects the *oracle* from the implementation's misreading also blinds the *search* — and
> those two things are separable.
>
> So: let a code-reading agent choose the inputs, and put the specification-anchored oracle
> in front of every accusation it makes. **Six of nine instead of five, at exactly the same
> false-alarm rate** — and it is the only system that catches both of the defects that are
> genuine specification violations.
>
> One withdrawal did that. The agent emitted a sound counterexample next to an unsound one,
> and under the scoring rule a single unsound test throws the whole case away. The oracle —
> which never sees the test, its reasoning, or the code — disagreed with the bad one, and
> the good one was credited. A stage that can only *remove* a test cannot invent a finding."

---

## Part 6 — 3:40–4:20 · The finding that outlives the project

**SHOW: Window A.** Run this live — about a minute:

```bash
python scripts/label_spec_visible.py
```

It prints: `buggy cases: 16   spec-visible: 3   under-determined: 13`

> "Chasing that turned up something about the benchmark rather than the agent.
>
> These defects were labelled by differentially fuzzing each implementation against a
> reference — the standard cheap way to build a defect corpus. But that means *differs from
> the reference*, not *violates the specification*, and two correct implementations differ
> freely wherever the specification is silent.
>
> Run each task's authoritative, standard-traced suite against every case labelled buggy:
> **thirteen of sixteen violate nothing the specification states.** And most of the
> detections that make a code-reading agent look good are on exactly those cases.
>
> On a benchmark built this way, the way to score well is to guess what the reference author
> would have written. A verifier that accuses only when the specification determines the
> answer stays silent — and is right to. **If you build agent evaluations by diffing against
> a reference, that is what you are grading.**"

---

## Part 7 — 4:20–4:50 · Changelog, and close

**SHOW: Window B.** Click `CHANGELOG.md`, scroll the summary table slowly.

> "Thirty-two iterations, each with the evidence that drove the next decision.
>
> **The change that contributed most was not to the agent.** It was iteration 24 — making
> the grader treat a sandbox timeout as inconclusive instead of as an observation. Before
> that, the headline numbers moved depending on how loaded the machine was. No conclusion
> here was trustworthy until that was fixed.
>
> **One experiment I removed:** telling the adversary to *search* the input space with
> property-based testing instead of guessing a single input. It worked as an intervention —
> property probes went from eight percent of its output to fifty — and detection did not
> move at all. Rejected on the dev split, never promoted.
>
> Everything you have seen replays offline from committed recordings, with no API key and no
> network."

**FINAL FRAME: Window A.** Run:

```bash
make reproduce-quick
```

Let the first few lines appear, then stop recording. The full run takes about fifteen
minutes — you are filming that it *starts*, not that it finishes.

---

## If you run long

Cut the `PREREGISTRATION.md` click in Part 2, and shorten the changelog scroll in Part 7.
**Never cut Part 4** — the admission that it failed is the spine of the whole thing.
