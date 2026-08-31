"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.  The
generator is domain-aware on purpose: a uniformly random header string is
malformed with probability ~1 and would only ever exercise the "ignore the
header" path, while uniformly random offsets against a large ``length`` would
essentially never land on the boundaries where RFC 7233 section 2.1 actually
bites.

So byte positions are drawn from a small pool anchored to the representation
length -- ``0``, ``1``, ``length - 1``, ``length``, ``length + 1``, ``2 *
length`` -- which is exactly where the clamping rule, the unsatisfiable
first-byte-pos rule and the oversized-suffix rule differ from each other.
Suffix lengths are drawn from the same pool so that ``-0`` and
``-(length + k)`` come up often.  Roughly one element in twelve is deliberately
malformed and one header in twenty carries a bad unit or stray whitespace, to
keep the "malformed headers are ignored" path covered; ``length == 0`` shows up
about one time in twenty-five.
"""

from __future__ import annotations

import random

# Representation lengths, biased small so that boundary positions are reachable.
LENGTHS = [0, 1, 2, 3, 5, 10, 10, 64, 100, 1000, 1000, 4096, 10000]

# Elements that must make the whole header malformed (and so ignored).
BAD_ELEMENTS = [
    "-",
    "abc",
    "0-1-2",
    "0 - 1",
    "+5-9",
    "1.5-2",
    "-1x",
    "0x10-",
    " 3-4 5",
]

# Whole headers that must be ignored outright.
BAD_HEADERS = [
    "",
    "0-499",
    "bytes",
    "bytes=",
    "bytes = 0-1",
    "items=0-5",
    "bytes=0-1;q=1",
    "none",
]


def _pos(rng: random.Random, length: int) -> int:
    """A byte position drawn from the corners of the [0, length] boundary."""
    pool = [0, 0, 1, length - 1, length, length, length + 1, 2 * length, length // 2]
    value = rng.choice(pool)
    return value if value >= 0 else 0


def _digits(rng: random.Random, value: int) -> str:
    """Render a position, occasionally with the leading zeroes the grammar allows."""
    if rng.random() < 0.08:
        return "0" * rng.randint(1, 3) + str(value)
    return str(value)


def _element(rng: random.Random, length: int) -> str:
    roll = rng.random()
    if roll < 0.08:
        return rng.choice(BAD_ELEMENTS)
    if roll < 0.30:
        # suffix-byte-range-spec, including the unsatisfiable "-0"
        return "-" + _digits(rng, _pos(rng, length))
    first = _pos(rng, length)
    if roll < 0.52:
        return _digits(rng, first) + "-"  # open ended, runs to the end
    last = _pos(rng, length)
    if last < first and rng.random() < 0.75:
        first, last = last, first  # mostly keep it a valid spec
    return _digits(rng, first) + "-" + _digits(rng, last)


def sample(rng: random.Random) -> tuple[tuple, dict]:
    length = rng.choice(LENGTHS) if rng.random() > 0.04 else 0
    if rng.random() < 0.05:
        return (rng.choice(BAD_HEADERS), length), {}
    count = rng.choices([1, 2, 3, 4], weights=[6, 3, 2, 1])[0]
    elements = [_element(rng, length) for _ in range(count)]
    if rng.random() < 0.10:
        elements.insert(rng.randint(0, len(elements)), "")  # empty list element
    separator = rng.choice([",", ", ", " ,", ",\t"])
    return ("bytes=" + separator.join(elements), length), {}


# Inputs that are always tried first, before random sampling. These encode the
# corners RFC 7233 section 2.1 calls out by name, plus the error cases.
SEEDS: list[tuple[tuple, dict]] = [
    (("bytes=0-499", 1000), {}),          # first 500 bytes, inclusive on both ends
    (("bytes=0-0", 1000), {}),            # a single byte
    (("bytes=-1", 1000), {}),             # the final byte, as a suffix
    (("bytes=500-", 1000), {}),           # open ended, runs to the end
    (("bytes=-500", 1000), {}),           # suffix form of the same range
    (("bytes=0-9999", 1000), {}),         # last-byte-pos clamped to length - 1
    (("bytes=-5000", 1000), {}),          # suffix longer than the representation
    (("bytes=0-0,-1", 1000), {}),         # the RFC's first-and-last-byte idiom
    (("bytes=100-199,5000-5100,0-0", 1000), {}),  # drop unsatisfiable, keep order
    (("bytes=0-99,50-149", 1000), {}),    # overlapping, neither merged nor sorted
    (("bytes=0-0, ,-1", 1000), {}),       # OWS and an empty list element
    (("Bytes=007-009", 1000), {}),        # case-insensitive unit, leading zeroes
    (("bytes=-0", 1000), {}),             # unsatisfiable: raises
    (("bytes=1000-1200", 1000), {}),      # first-byte-pos past the end: raises
    (("bytes=2-1", 1000), {}),            # last < first: malformed, so ignored
    (("items=0-5", 1000), {}),            # unrecognised unit: ignored
    (("bytes=0-0", 0), {}),               # empty representation: raises
    (("bytes=0-0", -1), {}),              # invalid argument: ValueError
]
