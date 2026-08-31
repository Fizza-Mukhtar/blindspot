"""Runtime configuration.

Everything that could make a run non-reproducible is funnelled through this
module: provider selection, model identity, temperature, seeds, timeouts and
paths.  ``RunConfig.fingerprint()`` is embedded in every result file so a
number can always be traced back to the exact configuration that produced it.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from .types import canonical_json, sha256_text

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECTRAP_DIR = REPO_ROOT / "spectrap"
CASES_DIR = SPECTRAP_DIR / "cases"
TASKS_DIR = SPECTRAP_DIR / "tasks"
CASSETTE_DIR = REPO_ROOT / "cassettes"
RESULTS_DIR = REPO_ROOT / "results"
TRAJECTORY_DIR = REPO_ROOT / "trajectories"
MEMORY_PATH = REPO_ROOT / "src" / "blindspot" / "agents" / "archetypes.yaml"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

Provider = Literal["replay", "claude_cli", "anthropic", "openai", "mock"]

# --------------------------------------------------------------------------- #
# Model aliases.
#
# Stages are addressed by ROLE, not by model id, so a whole configuration can
# be re-pointed at a different model family with one flag.  This is what makes
# the cross-model generalisation run (`--forged-by`) a one-liner.
# --------------------------------------------------------------------------- #

MODEL_ALIASES: dict[str, dict[str, str]] = {
    "anthropic": {
        "fast": "claude-haiku-4-5-20251001",
        "smart": "claude-sonnet-5",
    },
    "claude_cli": {
        "fast": "haiku",
        "smart": "sonnet",
    },
    "openai": {
        "fast": "gpt-4.1-mini",
        "smart": "gpt-4.1",
    },
    "mock": {"fast": "mock-fast", "smart": "mock-smart"},
    "replay": {"fast": "replay-fast", "smart": "replay-smart"},
}

# USD per million tokens.  Used only for the cost column of the results table;
# a missing entry degrades to 0.0 rather than crashing a run.
PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "haiku": (1.00, 5.00),
    "sonnet": (3.00, 15.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
}


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader.

    Deliberately dependency-free and non-overriding: a variable already present
    in the real environment always wins, so CI secrets are never shadowed by a
    stale local file.
    """
    path = path or (REPO_ROOT / ".env")
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class RunConfig:
    """One immutable description of how a run should behave."""

    provider: Provider = "replay"

    # `provider` chooses the TRANSPORT.  `model_family` chooses the model
    # NAMESPACE, and the two are deliberately separate: a cassette recorded
    # through the Claude Code CLI is keyed on the model id `sonnet`, and replay
    # must resolve to that same id or it would never find the recording.
    # Defaulting the family to claude_cli therefore makes `--provider replay`
    # able to play back what `--provider claude_cli --record` wrote.
    model_family: str = "claude_cli"

    # Role -> alias ("fast" | "smart") or an explicit model id.
    model_fast: str = "fast"
    model_smart: str = "smart"
    temperature: float = 0.0
    max_tokens: int = 4096
    seed: int = 20260828

    # Agent behaviour knobs.  Every one of these is an ablation switch.
    information_barrier: bool = True
    ambiguity_gate: bool = True
    referee: bool = True
    # Does the referee see the whole specification, or only the clause the
    # obligation was derived from?  Clause-only adjudication upheld a false
    # accusation whose input a *different* clause governed, so the default is
    # the whole document; the switch keeps that claim measurable.
    referee_full_spec: bool = True
    # An independent reading of the specification that never sees the probe's
    # claim, used to withdraw findings the referee upheld under anchoring.
    # It can only remove an accusation, never create one.
    oracle: bool = True
    memory: bool = True
    # May the adversary read the implementation when choosing *inputs*?
    #
    # The pre-registered configuration says no, and that configuration detects
    # 1/9 held-out defects: working from the specification alone, it never
    # guesses the one input that breaks the code.  The barrier that protects
    # the *oracle* from the implementation's misreading also blinds the
    # *search*, and those are separable.  With this on, the expected value
    # still comes only from the barrier-attested obligation ledger; the code is
    # used solely to decide where to aim.
    adversary_sees_impl: bool = False
    # Should the adversary be told to *search* the input domain rather than pick
    # one input?  Left open, it picks a single hand-picked value 89% of the time.
    # This changes what it does with the information it already has; it does not
    # give it any more.
    prefer_search_probes: bool = False
    property_probes: bool = True
    shrink: bool = True
    # Should the adversary see the implementation's docstrings?  Off by default:
    # a docstring is author prose and can restate the very misreading the
    # barrier exists to break.  Kept as a switch so that claim is measured.
    surface_docstrings: bool = False

    max_obligations: int = 10
    probes_per_obligation: int = 1
    repair_attempts: int = 2
    concurrency: int = 6
    # Hard ceiling on simultaneous model calls, process-wide.  0 means "use
    # `concurrency`".  It is separate from `concurrency` because the thread
    # pools nest: without this the real limit was `concurrency ** 2`.
    max_inflight: int = 0

    sandbox_timeout_s: float = 20.0
    llm_timeout_s: float = 300.0
    llm_retries: int = 3

    record: bool = False  # write cassettes while running live
    strict_replay: bool = True  # a cassette miss is a hard error

    cassette_dir: Path = field(default=CASSETTE_DIR)
    results_dir: Path = field(default=RESULTS_DIR)
    trajectory_dir: Path = field(default=TRAJECTORY_DIR)

    def resolve(self, role: Literal["fast", "smart"]) -> str:
        """Map a role to a concrete model id within the active model family."""
        requested = self.model_fast if role == "fast" else self.model_smart
        table = MODEL_ALIASES.get(self.model_family, {})
        return table.get(requested, requested)

    def price(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rate_in, rate_out = PRICING.get(model, (0.0, 0.0))
        return round(
            (input_tokens / 1_000_000) * rate_in + (output_tokens / 1_000_000) * rate_out, 6
        )

    def ablation_flags(self) -> dict[str, bool]:
        return {
            "information_barrier": self.information_barrier,
            "ambiguity_gate": self.ambiguity_gate,
            "referee": self.referee,
            "referee_full_spec": self.referee_full_spec,
            "oracle": self.oracle,
            "memory": self.memory,
            "adversary_sees_impl": self.adversary_sees_impl,
            "prefer_search_probes": self.prefer_search_probes,
            "property_probes": self.property_probes,
            "shrink": self.shrink,
            "surface_docstrings": self.surface_docstrings,
        }

    def fingerprint(self) -> str:
        """Stable hash of everything that can change a result."""
        payload = {
            k: (str(v) if isinstance(v, Path) else v)
            for k, v in asdict(self).items()
            if k
            not in {
                "cassette_dir",
                "results_dir",
                "trajectory_dir",
                "concurrency",
                "max_inflight",
                "record",
            }
        }
        # Transport is excluded on purpose: replaying a cassette recorded under
        # `claude_cli` must produce the same fingerprint as the live run that
        # wrote it.  The model family is NOT excluded -- it changes the answer.
        payload.pop("provider", None)
        payload["models"] = [self.resolve("fast"), self.resolve("smart")]
        return sha256_text(canonical_json(payload))[:16]


def config_from_env(**overrides: object) -> RunConfig:
    load_dotenv()
    provider = os.environ.get("BLINDSPOT_PROVIDER", "replay")
    base: dict[str, object] = {"provider": provider}
    # A live transport implies its own model namespace; `replay` inherits the
    # namespace that was recorded, which BLINDSPOT_MODEL_FAMILY can override
    # when replaying cassettes recorded against a different backend.
    if provider != "replay":
        base["model_family"] = provider
    family = os.environ.get("BLINDSPOT_MODEL_FAMILY")
    if family:
        base["model_family"] = family
    base.update(overrides)
    return RunConfig(**base)  # type: ignore[arg-type]
