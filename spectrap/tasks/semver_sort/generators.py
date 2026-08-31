"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.  The
generator is domain-aware on purpose: uniform random strings would almost
never reach the interesting corner of SemVer precedence, so the space is
biased towards the identifiers where the standard's rules actually bite.
"""

from __future__ import annotations

import random

CORE = ["0.1.0", "1.0.0", "1.0.1", "1.2.0", "1.10.0", "2.0.0", "10.0.0"]
PRERELEASE = [
    "",
    "-alpha",
    "-alpha.1",
    "-alpha.2",
    "-alpha.11",
    "-alpha.beta",
    "-beta",
    "-beta.2",
    "-beta.11",
    "-rc.1",
    "-rc.2",
    "-rc.10",
    "-0",
    "-1",
    "-11",
    "-x.7.z.92",
    "-x-y-z.-",
    "-A",
    "-a",
]
BUILD = ["", "+build.1", "+build.99", "+exp.sha.5114f85", "+21AF26D3-117B344092BD"]
PREFIX = ["", "v"]


def _tag(rng: random.Random) -> str:
    return (
        rng.choice(PREFIX)
        + rng.choice(CORE)
        + rng.choice(PRERELEASE)
        + rng.choice(BUILD)
    )


def sample(rng: random.Random) -> tuple[tuple, dict]:
    size = rng.randint(0, 9)
    tags = [_tag(rng) for _ in range(size)]
    return (tags,), {}


# A handful of inputs that are always tried first, before random sampling.
# These encode the corners the specification calls out by name.
SEEDS: list[tuple[tuple, dict]] = [
    (([],), {}),
    ((["1.0.0"],), {}),
    (
        (
            [
                "1.0.0",
                "1.0.0-rc.1",
                "1.0.0-beta.11",
                "1.0.0-beta.2",
                "1.0.0-beta",
                "1.0.0-alpha.beta",
                "1.0.0-alpha.1",
                "1.0.0-alpha",
            ],
        ),
        {},
    ),
    ((["1.0.0-alpha.11", "1.0.0-alpha.beta"],), {}),  # numeric ranks below alphanumeric
    ((["1.0.0-rc.10", "1.0.0-rc.2"],), {}),  # numeric identifiers compare numerically
    ((["1.0.0-alpha", "1.0.0-alpha.1"],), {}),  # more identifiers wins
    ((["1.0.0+build.99", "1.0.0+build.1"],), {}),  # build metadata ignored -> stable tie
    ((["v2.0.0", "1.10.0", "1.9.0"],), {}),  # numeric core, decorative v preserved
    ((["1.0.0-A", "1.0.0-a"],), {}),  # ASCII order: uppercase before lowercase
    ((["1.0.0-01"],), {}),  # invalid: leading zero in numeric identifier
    ((["1.01.0"],), {}),  # invalid: leading zero in core
    ((["1.0.0-"],), {}),  # invalid: empty pre-release
    ((["1.0"],), {}),  # invalid: not three parts
]
