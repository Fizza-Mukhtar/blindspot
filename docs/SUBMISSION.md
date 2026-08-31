# Submission checklist

Everything the brief asks for, where it is, and what is left to do by hand.

---

## Before you submit — two commands

```bash
make check        # lint, types, 114 tests, 297 corpus checks, doc references   (~15 min)
make package      # builds blindspot-submission.zip and refuses if it holds a secret
```

`make package` matters more than it looks. **`.env` in this working tree contains a live
`CLAUDE_CODE_OAUTH_TOKEN`.** It is gitignored, which protects a `git push` and does nothing
at all for a hand-made zip — so do not zip the folder yourself. The packaging script builds
from an allow-list and then scans every included file for credential-shaped strings, and
deletes the archive rather than writing one that carries a secret (Rule Book #08).

---

## The four required deliverables

| # | Deliverable | Where | Status |
|---|---|---|---|
| 1 | Solution code + improvement changelog | the repository · [`CHANGELOG.md`](../CHANGELOG.md) — 31 iterations, each with the evidence that drove the next decision, the removed experiments, the main failure mode and the hot take | **done** |
| 2 | Reproduction guide | [`REPRODUCE.md`](../REPRODUCE.md) — clean-environment walkthrough, exact commands, versions, measured runtimes, cost | **done** |
| 3 | Solution video (≤ 5 min) | [`VIDEO.md`](VIDEO.md) — shot list with timings and the exact commands to run on camera | **you must record it** |
| 4 | Agent trajectories | [`trajectories/`](../trajectories/) — 443 JSONL runs + a self-contained `viewer.html`; curated entry points in [`trajectories/README.md`](../trajectories/README.md) | **done** |

Also included because the brief asks for them elsewhere: the instructions that shape each
agent ([`src/blindspot/prompts/`](../src/blindspot/prompts/), one reviewable Markdown file
per agent) and the tool disclosure ([README §10](../README.md#10-what-existed-before-this-competition)).

---

## Recording the video

Read [`VIDEO.md`](VIDEO.md) first; it is written to be read aloud. Two things to get right:

- **Lead with the negative result.** The pre-registered hypothesis was refuted, and the
  submission is stronger for saying so in the first thirty seconds than for burying it.
  The repaired configuration beating the baseline lands harder *after* that, not instead
  of it.
- **Check the numbers against `results/summary.json` before recording.** The script quotes
  them, but the file is the source of truth.

Before you start:

```bash
make reproduce-quick   # ~15 min, confirms the repo is in the state you are filming
make trace             # rebuilds trajectories/viewer.html
make demo              # the shot-2 walkthrough, offline
```

---

## The rule book, line by line

| Rule | How this submission satisfies it |
|---|---|
| 01 Build with tools you know | Python, pytest, Hypothesis, Pydantic — all used as published |
| 02 What existed before vs. what you added | [README §10](../README.md#10-what-existed-before-this-competition); everything here was written for this challenge, and the coding-agent use is disclosed there |
| 03 Licences and service terms | Apache-2.0; dependencies used as published; model access via a documented headless mode |
| 04 Consequential actions sandboxed, human approval | Every model-written test runs in an isolated sandbox with no network. The consequential act — accusing an engineer's code — is gated: an unresolved ambiguity is *never* reported as a defect ([`decisions/`](../decisions/README.md)) |
| 05 A qualified human reviewer in the loop | `blindspot decide` routes genuine specification gaps to a person. The published run escalated 93 questions and answered none, because a benchmark run has no qualified human to ask |
| 06 Legal, ethical use case | Auditing code written from public specifications. No personal data anywhere |
| 07 Data you may share | Every task is built from a public standard (RFC, BIPM, IEC, semver.org). All implementations are model-generated for this project |
| 08 Credentials outside the submission | `.env` gitignored *and* excluded by `make package`, which scans the archive and refuses to write one containing a secret |
| 09 Every claim connected to evidence | Every number in the README is generated from `results/` by `scripts/update_readme.py`, and `make results` fails if prose and results disagree. `scripts/check_docs.py` verifies every path and command named in the docs exists. `make verify-citations` re-queries arXiv for every reference |
| 10 Enough access to reproduce | `make reproduce` replays all 330 runs offline with no API key and asserts the per-case table matches — currently **330/330 exact** |

---

## What a judge should look at first

1. **[README](../README.md) §"The result, first"** — 90 seconds; the whole story including the refutation.
2. **`make reproduce-quick`** — verify it rather than believe it.
3. **[PREREGISTRATION.md §8](../PREREGISTRATION.md#8-deviations-from-this-plan)** — what was
   predicted, what happened, and every deviation recorded rather than absorbed.
4. **[CHANGELOG.md](../CHANGELOG.md)** — the summary table reads top to bottom in ten
   minutes; iterations 22–31 are where the held-out split broke things.
5. **`trajectories/viewer.html`** — double-click, no server.
