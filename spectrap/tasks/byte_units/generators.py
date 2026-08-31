"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.

Uniform random integers are useless here: a byte count drawn uniformly from a
wide range is almost never within a few bytes of a unit boundary, of an exact
``.x5`` rounding tie, or of the point where rounding promotes a value into the
next unit.  Those three neighbourhoods are where every disagreement lives, so
the sampler spends most of its budget on them, in both prefix systems, and
mixes in negatives, sub-divisor byte counts, values above the top of the
ladder, and a small fraction (~12%) of wrong-typed inputs that must raise
``TypeError``.
"""

from __future__ import annotations

import random

_BAD_VALUES: list[object] = [
    1000.0,
    0.0,
    1.5,
    -1024.0,
    True,
    False,
    "1000",
    None,
    (1000,),
]


def _boundary(rng: random.Random, base: int) -> int:
    """A multiple of a unit divisor, nudged by a few bytes either way."""
    exponent = rng.randint(0, 6)
    multiple = rng.choice([1, 1, 1, 2, 3, 9, 10, 512, 999, 1023, 1024, 1500])
    return base**exponent * multiple + rng.randint(-2, 2)


def _rounding_tie(rng: random.Random, base: int) -> int:
    """Land on (or within a byte of) an exact ``.x5`` half-way display value."""
    exponent = rng.randint(1, 5)
    # Odd numerator over 20 => a value of the form d.d5 in the chosen unit.
    numerator = 2 * rng.randint(0, 40 * base // 10) + 1
    return base**exponent * numerator // 20 + rng.randint(-1, 1)


def _promotion(rng: random.Random, base: int) -> int:
    """Just under a unit boundary, in the zone where rounding promotes.

    ``base**(e+1) - base**e/20`` is the exact point at which the display value
    in unit ``e`` rounds up to ``base``.0 and must be promoted.
    """
    exponent = rng.randint(1, 5)
    edge = base ** (exponent + 1) - base**exponent // 20
    return edge + rng.randint(-2, 2)


def _small(rng: random.Random, base: int) -> int:
    """Byte-range magnitudes, where no decimal point is printed."""
    return rng.choice([0, 1, 9, 999, 1000, 1023, 1024, 1025, base - 1, base])


def _huge(rng: random.Random, base: int) -> int:
    """Past the top of the ladder, where the integer part keeps growing."""
    return base**5 * rng.randint(1, 5000) + rng.randint(-3, 3)


def sample(rng: random.Random) -> tuple[tuple, dict]:
    if rng.random() < 0.12:
        return (rng.choice(_BAD_VALUES),), {}

    binary = rng.random() < 0.5
    base = 1024 if binary else 1000
    strategy = rng.choice(
        [_boundary, _boundary, _rounding_tie, _rounding_tie, _promotion, _small, _huge]
    )
    n = strategy(rng, base)
    if rng.random() < 0.25:
        n = -n

    # Exercise both the keyword form and the default (SI) path.
    if binary:
        return (n,), {"binary": True}
    if rng.random() < 0.5:
        return (n,), {}
    return (n,), {"binary": False}


# Hand-picked inputs tried before random sampling.  These pin every corner the
# ticket and the two standards name explicitly.
SEEDS: list[tuple[tuple, dict]] = [
    ((0,), {}),  # zero stays in bytes, no decimal point
    ((999,), {}),  # SI: below the divisor, printed exactly
    ((1000,), {}),  # SI: lowercase k -> "1.0 kB"
    ((1024,), {}),  # SI: 1024 is NOT a kilobyte boundary
    ((1000,), {"binary": True}),  # IEC: 1000 is still plain bytes
    ((1023,), {"binary": True}),  # IEC: last byte-range value
    ((1024,), {"binary": True}),  # IEC: uppercase K -> "1.0 KiB"
    ((999_949,), {}),  # SI: rounds to 999.9 kB, no promotion
    ((999_950,), {}),  # SI: rounds to 1000.0 kB -> promoted to 1.0 MB
    ((1_048_575,), {"binary": True}),  # IEC: rounds to 1024.0 KiB -> 1.0 MiB
    ((1150,), {}),  # round half up on an exact .x5 tie -> 1.2 kB
    ((-1500,), {}),  # negative keeps the sign, formats the magnitude
    ((-999,), {"binary": True}),  # negative inside the byte range
    ((1_500_000_000_000_000_000,), {}),  # above PB -> 1500.0 PB
    ((2**60,), {"binary": True}),  # above PiB -> 1024.0 PiB
    ((1000.0,), {}),  # invalid: float, must raise TypeError
    ((True,), {}),  # invalid: bool is not a byte count
]
