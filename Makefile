# Blindspot — one entry point per thing a reader might want to do.
#
# The single most important target is `make reproduce`: it regenerates every
# published number from committed cassettes, offline, with no API key, and fails
# loudly if anything drifts.  It is not fast -- it re-executes every generated
# test against two targets -- so `make reproduce-quick` does the headline systems
# only.  No model is ever called by either.
#
# Every target works on Linux, macOS and Windows.  No recipe uses shell-specific
# syntax: `VAR=value cmd` is POSIX-only and is a syntax error under cmd.exe,
# which is the shell GNU make picks on Windows outside git-bash.  Options go
# on the command line instead.

PY ?= python
PIP ?= $(PY) -m pip
BLINDSPOT ?= $(PY) -m blindspot.cli

.DEFAULT_GOAL := help
.PHONY: help install install-dev doctor test test-fast lint typecheck check \
        check-docs triage-audit verify-corpus verify-citations crosscheck \n        reproduce reproduce-quick \
        eval eval-ablations eval-dev record forge learn split trace demo results \
        freeze freeze-corpus label-spec-visible package clean distclean
# --------------------------------------------------------------------------- #

help:
	@echo ""
	@echo "  Blindspot — adversarial verification for AI-written code"
	@echo ""
	@echo "  FIRST TIME"
	@echo "    make install          install the package (no model access needed)"
	@echo "    make doctor           check the environment is sane"
	@echo ""
	@echo "  THE HEADLINE RESULT  (no API key, no network, offline)"
	@echo "    make reproduce-quick  replay the headline systems only  (~15 min)"
	@echo "    make reproduce        replay everything incl. ablations (~40 min)"
	@echo "                          and assert it matches results/expected/"
	@echo ""
	@echo "  EVIDENCE"
	@echo "    make test             the test suite (offline, deterministic)"
	@echo "    make verify-corpus    prove every benchmark label mechanically"
	@echo "    make label-spec-visible  re-derive which defects the spec really pins down"
	@echo "    make crosscheck       compare each reference to an independent oracle"
	@echo "    make check            lint + types + tests + corpus + doc references"
	@echo "    make triage-audit     every finding vs the grader's own verdict"
	@echo "    make verify-citations every arXiv reference, against the live API"
	@echo ""
	@echo "  DEMO"
	@echo "    make demo             audit one real case end to end, offline"
	@echo "    make trace            render agent trajectories to a single HTML file"
	@echo ""
	@echo "  SUBMIT"
	@echo "    make package          build the archive; refuses if a secret is inside"
	@echo ""
	@echo "  LIVE  (needs model access — see REPRODUCE.md)"
	@echo "    make record           re-run the sweep live and write cassettes (resumable)"
	@echo "    make freeze           promote a recorded sweep to results/expected/"
	@echo "    make forge            rebuild the SpecTrap corpus from the task library"
	@echo "    make learn            rebuild archetype memory from the dev split"
	@echo ""

# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,live]"

doctor:
	$(BLINDSPOT) doctor

# --------------------------------------------------------------------------- #
# Evidence
# --------------------------------------------------------------------------- #

test:
	$(PY) -m pytest tests -q

test-fast:
	$(PY) -m pytest tests -q -m "not slow"

lint:
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

typecheck:
	$(PY) -m mypy

check-docs:
	$(PY) scripts/check_docs.py --strict

triage-audit:
	$(PY) scripts/triage_audit.py

verify-corpus:
	$(PY) scripts/verify_corpus.py --json results/corpus_integrity.json
	$(PY) scripts/label_spec_visible.py --check
	$(PY) scripts/freeze_corpus.py --check

# The only check that needs the network, which is why it is not in `make check`.
verify-citations:
	$(PY) scripts/verify_citations.py --strict

crosscheck:
	$(PY) scripts/run_crosscheck.py --json results/crosscheck.json

check: lint typecheck test verify-corpus check-docs
	@echo "all checks passed"

# --------------------------------------------------------------------------- #
# The reproduction path — offline, no credentials
# --------------------------------------------------------------------------- #

# The headline systems only, no ablations.  Same assertion, a fraction of the
# sandbox work, for a reader who wants the result verified before deciding
# whether to spend longer.
reproduce-quick:
	@echo ">> replaying the headline systems from committed cassettes (no API key)"
	$(BLINDSPOT) eval --provider replay \
		--split test \
		--systems self_tests baseline_direct baseline_agent blindspot blindspot_search agent_plus_oracle \
		--out results/reproduced
	$(PY) scripts/compare_results.py results/expected results/reproduced

reproduce:
	@echo ">> replaying the full benchmark from committed cassettes (no API key needed)"
	$(BLINDSPOT) eval --provider replay \
		--split test \
		--systems self_tests baseline_direct baseline_agent blindspot blindspot_search agent_plus_oracle \
		--ablations --ablation-clean 6 \
		--out results/reproduced
	$(PY) scripts/compare_results.py results/expected results/reproduced

eval:
	$(BLINDSPOT) eval --split test \
		--systems self_tests baseline_direct baseline_agent blindspot blindspot_search agent_plus_oracle \
		--out results

eval-ablations:
	$(BLINDSPOT) eval --split test --ablations --ablation-clean 6 \
		--systems self_tests baseline_direct baseline_agent blindspot blindspot_search agent_plus_oracle \
		--out results

eval-dev:
	$(BLINDSPOT) eval --split dev \
		--systems baseline_direct baseline_agent blindspot \
		--out results/dev

results:
	$(PY) scripts/update_readme.py --check

# Promote a freshly recorded sweep to the committed reference that
# `make reproduce` asserts against.  Kept as an explicit, separate step: the
# published numbers should only ever move when somebody means to move them.
freeze:
	$(PY) scripts/freeze_results.py

# Re-hash the benchmark.  Only after deliberately changing it -- the lock is
# what makes "frozen before the run" checkable rather than asserted.
freeze-corpus:
	$(PY) scripts/freeze_corpus.py

# Re-derive, by execution, which buggy cases actually violate their
# specification and which merely differ from the reference.
label-spec-visible:
	$(PY) scripts/label_spec_visible.py

# --------------------------------------------------------------------------- #
# Live targets (model access required)
# --------------------------------------------------------------------------- #

record:
	$(BLINDSPOT) eval --provider claude_cli --record --split test \
		--ablations --ablation-clean 6 \
		--systems self_tests baseline_direct baseline_agent blindspot blindspot_search agent_plus_oracle \
		--out results
	$(BLINDSPOT) cassettes

forge:
	$(BLINDSPOT) forge --provider claude_cli --record --variants 4 --clean-per-task 2

learn:
	$(BLINDSPOT) learn --provider claude_cli --record

split:
	$(BLINDSPOT) split

# --------------------------------------------------------------------------- #
# Demo
# --------------------------------------------------------------------------- #

demo:
	$(PY) scripts/demo.py

trace:
	$(BLINDSPOT) trace --out trajectories/viewer.html

# --------------------------------------------------------------------------- #

# Build the submission archive.  Refuses to write one containing anything
# credential-shaped -- `.env` is gitignored, which does nothing for a hand-made zip.
package:
	$(PY) scripts/package_submission.py

clean:
	$(PY) scripts/clean.py

distclean: clean
	rm -rf results/reproduced results/smoke .blindspot
