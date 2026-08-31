"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  The generator is
domain-aware on purpose.  Uniformly random decimal strings would essentially
never land *exactly* on a half-way value, and the half-way values are the only
place where ROUND_HALF_EVEN differs from ROUND_HALF_UP or from a float
round-trip.  So roughly half of the amounts here are constructed to be an exact
tie at the target precision, and the currency is drawn from a table whose
exponents are deliberately spread over 0, 2, 3 and 4 rather than being 2 the way
most real traffic is.  A minority of samples are malformed amounts (ValueError)
or codes missing from the table (KeyError).
"""

from __future__ import annotations

import random

# ISO 4217 exponents, https://www.iso.org/iso-4217-currency-codes.html
EXPONENTS: dict[str, int] = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "JPY": 0,
    "ISK": 0,
    "UGX": 0,
    "KWD": 3,
    "BHD": 3,
    "OMR": 3,
    "TND": 3,
    "CLF": 4,
}

# Weighted so the unusual exponents show up far more often than they would in
# production traffic.
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "JPY", "ISK", "UGX", "KWD", "KWD", "BHD", "OMR", "TND", "CLF", "CLF"]

INTEGER_PARTS = ["0", "1", "2", "3", "5", "7", "12", "99", "100", "1234", "1235", "1000000"]

MALFORMED = [
    "",
    "abc",
    "1.2.3",
    "12,34",
    "$1.00",
    "1 000.00",
    "--1",
    ".",
    "NaN",
    "sNaN",
    "Infinity",
    "-Infinity",
    "1,234.56",
    "USD 1.00",
]

UNKNOWN_CODES = ["usd", "XYZ", "", "US", "JPY ", "jpy", "ZZZ"]

SCIENTIFIC = ["1E+2", "-1.5e-3", "1.005E+1", "2.5E-1", "-1234.5E0", "6.25e-2", "1E-9", "-2.5E+3"]


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _fraction(rng: random.Random, exponent: int) -> str:
    """Fractional part, biased hard toward exact ties at ``exponent`` places."""
    roll = rng.random()
    if roll < 0.42:
        # Exact half-way value: `exponent` kept digits then a lone 5.
        return _digits(rng, exponent) + "5"
    if roll < 0.58:
        # A hair either side of the tie -- must NOT be treated as a tie.
        return _digits(rng, exponent) + "5" + rng.choice(["1", "9", "0001", "00000001"])
    if roll < 0.72:
        # Fewer decimals than the target: the result has to be zero-padded.
        return _digits(rng, rng.randint(0, exponent))
    if roll < 0.88:
        return _digits(rng, exponent + rng.randint(1, 3))
    return ""


def _amount(rng: random.Random, exponent: int) -> str:
    if rng.random() < 0.08:
        return rng.choice(SCIENTIFIC)
    sign = rng.choice(["", "", "", "", "-", "-", "+"])
    body = rng.choice(INTEGER_PARTS)
    fraction = _fraction(rng, exponent)
    text = sign + body + ("." + fraction if fraction else "")
    if rng.random() < 0.04:
        text = "  " + text + "  "  # surrounding whitespace is accepted
    return text


def sample(rng: random.Random) -> tuple[tuple, dict]:
    roll = rng.random()
    if roll < 0.07:
        # Unknown currency code -> KeyError, checked before the amount.
        return (_amount(rng, 2), rng.choice(UNKNOWN_CODES), dict(EXPONENTS)), {}
    if roll < 0.17:
        # Malformed amount -> ValueError.
        return (rng.choice(MALFORMED), rng.choice(CURRENCIES), dict(EXPONENTS)), {}
    currency = rng.choice(CURRENCIES)
    return (_amount(rng, EXPONENTS[currency]), currency, dict(EXPONENTS)), {}


# Tried before random sampling.  These cover every corner the ticket and the
# cited standards call out by name.
SEEDS: list[tuple[tuple, dict]] = [
    (("2.675", "USD", dict(EXPONENTS)), {}),      # tie up: 7 is odd  -> 2.68
    (("2.665", "USD", dict(EXPONENTS)), {}),      # tie stay: 6 even  -> 2.66
    (("8.835", "USD", dict(EXPONENTS)), {}),      # float round-trip gets this wrong
    (("-2.675", "USD", dict(EXPONENTS)), {}),     # negative tie, sign kept
    (("-0.125", "USD", dict(EXPONENTS)), {}),     # negative tie down to even
    (("1234.5", "JPY", dict(EXPONENTS)), {}),     # exponent 0, tie stays even, no point
    (("1235.5", "JPY", dict(EXPONENTS)), {}),     # exponent 0, tie goes up
    (("1.2345", "KWD", dict(EXPONENTS)), {}),     # exponent 3
    (("0.12345", "CLF", dict(EXPONENTS)), {}),    # exponent 4
    (("1E+2", "USD", dict(EXPONENTS)), {}),       # scientific notation in
    (("5", "USD", dict(EXPONENTS)), {}),          # zero padding out
    (("-0.004", "USD", dict(EXPONENTS)), {}),     # negative zero normalises
    (("-0.4", "JPY", dict(EXPONENTS)), {}),       # negative zero at exponent 0
    (("1234567.891", "USD", dict(EXPONENTS)), {}),  # no thousands separator
    (("abc", "USD", dict(EXPONENTS)), {}),        # invalid: ValueError
    (("1.00", "XYZ", dict(EXPONENTS)), {}),       # unknown code: KeyError
]
