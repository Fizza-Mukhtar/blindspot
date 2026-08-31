"""Statistics for a deliberately small benchmark.

Pure standard library -- no numpy, no scipy -- so the reproduction path has no
compiled dependencies.

Three deliberate choices, each of which matters at n = 10:

* **Wilson score intervals**, not normal approximation.  At these counts the
  Wald interval famously produces intervals that fall outside [0, 1] and has
  actual coverage well below its nominal level.
* **Exact conditional McNemar** for paired binary outcomes, with the mid-p
  variant reported alongside.  The chi-square form is invalid below roughly 25
  discordant pairs, which is every comparison in this benchmark.
* **The power ceiling is stated before the result.**  With c = 0 baseline-only
  wins, exact two-sided McNemar gives p = 2^(1-b); reaching p < 0.05 therefore
  requires at least six system-only wins, no matter how large the observed
  difference looks.  Any comparison here is a preliminary signal, not a
  significance claim, and this module makes that explicit rather than leaving
  it to the reader.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

Z_95 = 1.959963984540054


# --------------------------------------------------------------------------- #
# Proportions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Proportion:
    successes: int
    n: int
    lo: float
    hi: float

    @property
    def value(self) -> float:
        return self.successes / self.n if self.n else 0.0

    @property
    def pct(self) -> float:
        return 100.0 * self.value

    def render(self, decimals: int = 0) -> str:
        if not self.n:
            return "n/a"
        return (
            f"{self.successes}/{self.n} = {self.pct:.{decimals}f}% "
            f"[{100 * self.lo:.{decimals}f}, {100 * self.hi:.{decimals}f}]"
        )


def wilson(successes: int, n: int, z: float = Z_95) -> Proportion:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return Proportion(0, 0, 0.0, 0.0)
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    margin = (z / denominator) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return Proportion(successes, n, max(0.0, centre - margin), min(1.0, centre + margin))


# --------------------------------------------------------------------------- #
# Paired binary comparison
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class McNemar:
    b: int  # system succeeded, baseline failed
    c: int  # baseline succeeded, system failed
    n_discordant: int
    p_exact: float
    p_midp: float

    @property
    def significant(self) -> bool:
        return self.p_exact < 0.05

    def render(self) -> str:
        return (
            f"b={self.b}, c={self.c}, exact two-sided p={self.p_exact:.4f} "
            f"(mid-p={self.p_midp:.4f})"
        )


def _binom_tail(m: int, n: int) -> float:
    """sum_{i<=m} C(n, i) * 2^-n."""
    return sum(math.comb(n, i) for i in range(m + 1)) / (2**n)


def mcnemar_exact(system: Sequence[bool], baseline: Sequence[bool]) -> McNemar:
    """Exact conditional McNemar test, two-sided, with the mid-p variant."""
    if len(system) != len(baseline):
        raise ValueError("paired sequences must be the same length")
    b = sum(1 for s, t in zip(system, baseline, strict=True) if s and not t)
    c = sum(1 for s, t in zip(system, baseline, strict=True) if t and not s)
    n = b + c
    if n == 0:
        return McNemar(b, c, 0, 1.0, 1.0)
    m = min(b, c)
    tail = _binom_tail(m, n)
    p_exact = min(1.0, 2 * tail)
    point = math.comb(n, m) / (2**n)
    p_midp = min(1.0, 2 * (tail - 0.5 * point))
    return McNemar(b, c, n, p_exact, max(0.0, p_midp))


def mcnemar_power_ceiling(b: int, c: int) -> str:
    """One sentence stating what this discordance count can and cannot show."""
    n = b + c
    if n == 0:
        return "No discordant pairs: the two systems agreed on every case."
    if c == 0:
        needed = 6  # 2^(1-b) < 0.05  =>  b >= 6
        return (
            f"With c=0, exact two-sided McNemar gives p = 2^(1-b); reaching p < 0.05 "
            f"requires b >= {needed} system-only wins (observed b = {b})."
        )
    return f"{n} discordant pairs; exact conditional McNemar is the appropriate test at this n."


# --------------------------------------------------------------------------- #
# Effect size
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Bootstrap:
    delta: float
    lo: float
    hi: float
    iterations: int

    def render(self) -> str:
        return (
            f"Delta = {100 * self.delta:+.1f} pp, "
            f"95% percentile bootstrap [{100 * self.lo:+.1f}, {100 * self.hi:+.1f}] "
            f"(B={self.iterations})"
        )


def paired_bootstrap(
    system: Sequence[bool],
    baseline: Sequence[bool],
    *,
    iterations: int = 10_000,
    seed: int = 20260828,
) -> Bootstrap:
    """Percentile bootstrap over *cases* for the paired difference in rates."""
    n = len(system)
    if n == 0:
        return Bootstrap(0.0, 0.0, 0.0, 0)
    observed = (sum(system) - sum(baseline)) / n
    rng = random.Random(seed)
    deltas: list[float] = []
    indices = range(n)
    for _ in range(iterations):
        picks = [rng.choice(indices) for _ in indices]
        deltas.append(sum(system[i] - baseline[i] for i in picks) / n)
    deltas.sort()
    lo = deltas[int(0.025 * iterations)]
    hi = deltas[min(iterations - 1, int(0.975 * iterations))]
    return Bootstrap(observed, lo, hi, iterations)


# --------------------------------------------------------------------------- #
# Multiplicity
# --------------------------------------------------------------------------- #


def holm(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, tuple[float, bool]]:
    """Holm-Bonferroni step-down adjustment for the secondary comparisons."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, tuple[float, bool]] = {}
    running = 0.0
    for rank, (name, p) in enumerate(ordered):
        value = min(1.0, max(running, (m - rank) * p))
        running = value
        adjusted[name] = (value, value < alpha)
    return adjusted


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Agreement between two categorical labellings, corrected for chance.

    Used to report how closely the automated triage labels match the manual
    labels in ``results/manual_triage_labels.yaml``.  No headline metric depends
    on the automated label; kappa is how we say so with a number.
    """
    if len(a) != len(b) or not a:
        return float("nan")
    categories = sorted(set(a) | set(b))
    n = len(a)
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    expected = sum(
        (sum(1 for x in a if x == cat) / n) * (sum(1 for y in b if y == cat) / n)
        for cat in categories
    )
    if expected >= 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


# --------------------------------------------------------------------------- #
# Clustering
#
# The corpus contains several *independently generated implementations that
# carry the same defect* -- six byte_units variants all fail on the same
# witness.  They are distinct programs, so they are distinct cases, but their
# outcomes are far from independent: a system that reads the specification
# correctly gets all six or none.  Treating them as six observations would
# overstate the evidence, so intervals are also computed by resampling
# *defects* rather than cases.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClusteredRate:
    value: float
    lo: float
    hi: float
    n_cases: int
    n_clusters: int

    def render(self) -> str:
        return (
            f"{100 * self.value:.0f}% "
            f"[{100 * self.lo:.0f}, {100 * self.hi:.0f}] "
            f"({self.n_cases} cases in {self.n_clusters} defect group(s))"
        )


def cluster_bootstrap(
    outcomes: Sequence[bool],
    clusters: Sequence[str],
    *,
    iterations: int = 10_000,
    seed: int = 20260828,
) -> ClusteredRate:
    """Percentile bootstrap for a rate, resampling whole clusters.

    Each distinct value in ``clusters`` is one underlying defect.  Resampling
    at that level gives an interval that reflects how many *different* bugs
    were seen, not how many implementations happened to carry them.  With few
    clusters the interval is wide, which is the honest answer rather than a
    defect of the method.
    """
    if not outcomes:
        return ClusteredRate(0.0, 0.0, 0.0, 0, 0)

    groups: dict[str, list[bool]] = {}
    for outcome, cluster in zip(outcomes, clusters, strict=True):
        groups.setdefault(cluster, []).append(outcome)

    keys = sorted(groups)
    observed = sum(outcomes) / len(outcomes)
    if len(keys) < 2:
        return ClusteredRate(observed, 0.0, 1.0, len(outcomes), len(keys))

    rng = random.Random(seed)
    rates: list[float] = []
    for _ in range(iterations):
        picked = [groups[rng.choice(keys)] for _ in keys]
        flat = [value for group in picked for value in group]
        rates.append(sum(flat) / len(flat) if flat else 0.0)
    rates.sort()
    lo = rates[int(0.025 * iterations)]
    hi = rates[min(iterations - 1, int(0.975 * iterations))]
    return ClusteredRate(observed, lo, hi, len(outcomes), len(keys))
