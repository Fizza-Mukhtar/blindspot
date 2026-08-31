"""Independent oracle for PRICING-2317 (discount_stacking).

Deliberately structured differently from the obvious implementation:

  * no ``decimal`` module anywhere.  All arithmetic is exact rational
    arithmetic with ``fractions.Fraction``, so there is no quantization
    context, no global precision, and no reliance on
    ``Decimal.quantize(ROUND_HALF_EVEN)``.
  * round-half-even is implemented from first principles on integers:
    for a rational ``n/d`` (d > 0) scaled to cents, ``q, r = divmod(n, d)``
    and the tie ``2*r == d`` is broken toward the even ``q``.  This
    reproduces IEEE 754 / ROUND_HALF_EVEN semantics without importing it.
  * the running total is carried as an *integer number of cents*, so the
    "re-quantize after every step" requirement is structural rather than a
    call that could be forgotten.
  * the money grammar is checked with a single ``re.fullmatch`` and the
    numeric value is then reconstructed by hand from the digit groups,
    rather than by handing the string to a numeric constructor that would
    silently accept things the grammar forbids (``"1e3"``, ``"+5"``,
    ``" 5.00"``, ``"NaN"``, ``"Infinity"``, ``"5_0"``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from fractions import Fraction

ORACLE_NOTES = """
Based on: SPEC.md (PRICING-2317) for the algorithm, plus the cited grounding
document, Shopify Help Center "Discount combinations"
(https://help.shopify.com/en/manual/discounts/discount-combinations).

Implementation basis: exact rational arithmetic (fractions.Fraction) with a
hand-written round-half-even on integer cents (q, r = divmod(n, d); tie when
2*r == d resolved toward even q).  No decimal module, no float, no
Decimal.quantize.  The running total is carried as an int number of cents,
which makes "round after every step" (SPEC rule 3) structurally unavoidable.

Clauses checked
---------------
SPEC rule 1  : subtotal normalised to 2dp with the same rounding mode.
SPEC rule 2  : strict list order; percent -> rt*(100-p)/100, amount -> rt-a.
SPEC rule 3  : ROUND_HALF_EVEN after EVERY step.  Verified against the spec's
               own examples 5.025 -> 5.02 and 5.075 -> 5.08, and against
               task.yaml's 1.15 with 10% twice -> 0.94 (not 0.93).
SPEC rule 4  : clamp at 0.00, excess discarded, later steps operate on 0.00.
               (Round-then-clamp and clamp-then-round are provably identical
               here: a negative raw value can never round to a positive one,
               so this is not an ambiguity.)
SPEC rule 5  : empty stack -> subtotal normalised only.
SPEC rule 6  : exactly two fractional digits on the way out; "-0.00" is
               normalised to "0.00".
SPEC errors  : all six error clauses, all ValueError, validated at the moment
               the walk reaches the entry even after a clamp to zero.
Shopify doc  : "Discounts apply in the following order: product discounts ...
               order discounts apply to the revised subtotal after product
               discounts ... shipping discounts apply last", and "If two or
               more order discounts that provide a percentage off are applied
               to the same order, then both percentages are calculated on the
               original subtotal."

DISPUTED / possibly WRONG in SPEC.md
------------------------------------
1. The grounding is a misreading for the exact case the ticket uses to
   motivate itself.  SPEC.md's Background says a customer stacked 20% and 10%
   on EUR 100.00 and "the storefront quoted EUR 72.00", citing the Shopify
   page as authority.  The cited page says the opposite for two stacked
   PERCENTAGE ORDER discounts: "If two or more order discounts that provide a
   percentage off are applied to the same order, then both percentages are
   calculated on the original subtotal", with the page's own worked example
   being a $100 subtotal, 10% (WELCOME10) plus 20% (INFLUENCER20), giving
   "a total discount of $30 USD off" -> $70.00.  That is precisely the
   "70.00" the ticket calls the bug.  Successive application against the
   remaining amount is what the page describes ACROSS categories (a product
   discount, then an order discount on the revised subtotal), not for two
   percentages of the same category.  The ticket's arithmetic is a perfectly
   reasonable engine design and is fully self-specified, so this oracle
   implements the ticket; but task.yaml's claim that the grounding standard
   says "combined discounts apply successively to the amount remaining after
   the previous discount" is not supported by that URL for the percent+percent
   case the trap is built on.
2. The standard says nothing at all about rounding, half-even or otherwise.
   Rule 3 is invented by the ticket, not grounded.  (It is unambiguous as
   written, so it is not a defect in the ticket - only in the grounding claim.)
3. Genuinely under-determined: whether "negative" is a property of the VALUE
   or of the STRING.  "-0.00" and "-0" match the grammar and denote zero.
   This oracle treats negativity as value < 0, so "-0.00" is accepted and
   returns "0.00", consistent with "The sign of zero is not significant".
   A string-level reading ("starts with '-'") would raise.  The spec does not
   say which.
4. Not resolved by the spec (and listed as an open question in task.yaml):
   extra keys in a discount mapping.  This oracle ignores them.
5. Under-determined: SPEC.md types `discounts` as `list[dict]` but gives no
   error clause for a non-list.  This oracle simply iterates, so a non-
   iterable produces TypeError rather than ValueError.
6. Under-determined: SPEC.md says an element that "is not a mapping" raises.
   This oracle uses collections.abc.Mapping; reference.py appears to use
   `dict`, so a non-dict Mapping is rejected by the reference and accepted
   here.  Only reachable with a custom Mapping class; not fuzzed.

REFERENCE DEFECTS FOUND (see the last six KNOWN_VALUES)
--------------------------------------------------------
b1. reference.py accepts exactly one TRAILING NEWLINE in any money string --
    subtotal and discount value, both kinds -- because its regex is anchored
    with '$' rather than '\\Z'/re.fullmatch.  SPEC.md's grammar says
    "Nothing else: ... no whitespace".  apply_discounts("5.00\\n", []) returns
    "5.00" instead of raising ValueError.
b2. reference.py uses '\\d' rather than '[0-9]', so any Unicode Nd digit is
    accepted as money: apply_discounts("\\u0665.\\u0660\\u0660", []) returns
    "5.00", as does "\\uff15" (fullwidth 5) and "\\u0f25" (Tibetan 5).  Mixed
    scripts too: "5\\u0665" is read as 55.
""".strip()


# optional '-', one or more digits, optionally '.' + one or more digits.
_MONEY = re.compile(r"(-?)([0-9]+)(?:\.([0-9]+))?\Z")


def _parse_money(text: object, label: str) -> Fraction:
    """Exact Fraction for a string in the ticket's money grammar, else ValueError."""
    if not isinstance(text, str):
        raise ValueError(f"{label} is not a str: {text!r}")
    match = _MONEY.fullmatch(text)
    if match is None:
        raise ValueError(f"{label} is malformed: {text!r}")
    sign, whole, frac = match.group(1), match.group(2), match.group(3) or ""
    # Rebuild the value by hand from the digit groups: no numeric parser is
    # trusted with the raw string.
    magnitude = Fraction(int(whole + frac), 10 ** len(frac)) if frac else Fraction(int(whole))
    return -magnitude if sign else magnitude


def _round_half_even_cents(value: Fraction) -> int:
    """Round an exact rational number of EUROS to an integer number of CENTS.

    Half-even implemented from first principles on integers.  Python's divmod
    floors, so 0 <= r < d for d > 0 and the comparison 2*r vs d is exact.
    """
    scaled = value * 100
    numerator, denominator = scaled.numerator, scaled.denominator  # denominator > 0
    quotient, remainder = divmod(numerator, denominator)
    twice = 2 * remainder
    if twice > denominator:
        return quotient + 1
    if twice < denominator:
        return quotient
    # exact tie: go to the even neighbour
    return quotient if quotient % 2 == 0 else quotient + 1


def _format_cents(cents: int) -> str:
    """Integer cents -> decimal string with exactly two fractional digits."""
    if cents == 0:
        return "0.00"  # the sign of zero is not significant
    sign = "-" if cents < 0 else ""
    magnitude = abs(cents)
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def oracle(subtotal, discounts):
    # --- rule 1 / error clauses on the subtotal -------------------------
    start = _parse_money(subtotal, "subtotal")
    if start < 0:
        raise ValueError(f"subtotal is negative: {subtotal!r}")
    running = _round_half_even_cents(start)  # int cents

    # NOTE: no type check on ``discounts`` itself.  SPEC.md types it
    # ``list[dict]`` but states no error clause for a non-list, so a
    # non-iterable simply fails to iterate (TypeError).  An earlier draft of
    # this oracle raised ValueError there and disagreed with the reference;
    # the spec's silence makes the reference's behaviour the defensible one.
    # --- rule 2: walk in order, validating unconditionally --------------
    for index, entry in enumerate(discounts):
        if not isinstance(entry, Mapping):
            raise ValueError(f"discount {index} is not a mapping: {entry!r}")
        if "kind" not in entry:
            raise ValueError(f"discount {index} is missing 'kind': {entry!r}")
        if "value" not in entry:
            raise ValueError(f"discount {index} is missing 'value': {entry!r}")

        kind = entry["kind"]
        raw = entry["value"]
        if kind not in ("percent", "amount"):
            raise ValueError(f"discount {index} has unknown kind: {kind!r}")

        value = _parse_money(raw, f"discount {index} value")
        if value < 0:
            raise ValueError(f"discount {index} value is negative: {raw!r}")

        if kind == "percent":
            if value > 100:
                raise ValueError(f"discount {index} percent exceeds 100: {raw!r}")
            # running is in cents; the factor is exact, then re-quantized.
            new_value = Fraction(running, 100) * (100 - value) / 100
        else:
            new_value = Fraction(running, 100) - value

        running = _round_half_even_cents(new_value)  # rule 3, every step
        if running < 0:
            running = 0  # rule 4: clamp, discard the excess

    # --- rule 6 ---------------------------------------------------------
    return _format_cents(running)


KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # --- SPEC.md's own worked example table (67.50, not 65.00) ----------
    (("100.00", [{"kind": "percent", "value": "20"},
                 {"kind": "amount", "value": "5.00"},
                 {"kind": "percent", "value": "10"}]), {}, "67.50"),
    # --- same stack reordered, spec text: 95.00 -> 76.00 -> 68.40 ------
    (("100.00", [{"kind": "amount", "value": "5.00"},
                 {"kind": "percent", "value": "20"},
                 {"kind": "percent", "value": "10"}]), {}, "68.40"),
    # --- SPEC Background: 20% then 10% on 100.00 is 72.00 -------------
    # NOTE: the cited Shopify page's own example gives 70.00 for two
    # percentage ORDER discounts.  See ORACLE_NOTES item 1.
    (("100.00", [{"kind": "percent", "value": "20"},
                 {"kind": "percent", "value": "10"}]), {}, "72.00"),
    # --- SPEC rule 3, verbatim: 5.025 -> 5.02 and 5.075 -> 5.08 --------
    (("10.05", [{"kind": "percent", "value": "50"}]), {}, "5.02"),
    (("10.15", [{"kind": "percent", "value": "50"}]), {}, "5.08"),
    # --- round every step, not once at the end: 0.94, not 0.93 --------
    (("1.15", [{"kind": "percent", "value": "10"},
               {"kind": "percent", "value": "10"}]), {}, "0.94"),
    # --- rule 5: empty stack normalises only ---------------------------
    (("7.5", []), {}, "7.50"),
    # --- rule 1 normalisation is half-even too: 0.005 -> 0.00, 0.015 -> 0.02
    (("0.005", []), {}, "0.00"),
    (("0.015", []), {}, "0.02"),
    # --- rule 4: clamp, excess discarded, later steps see 0.00 ---------
    (("10.00", [{"kind": "amount", "value": "15.00"},
                {"kind": "percent", "value": "50"}]), {}, "0.00"),
    (("19.99", [{"kind": "percent", "value": "100"},
                {"kind": "amount", "value": "1.00"}]), {}, "0.00"),
    # --- 100% is a legal boundary, not an error ------------------------
    (("50.00", [{"kind": "percent", "value": "100"}]), {}, "0.00"),
    # --- 0% is a legal boundary and a no-op ----------------------------
    (("12", [{"kind": "percent", "value": "0"}]), {}, "12.00"),
    # --- error clauses --------------------------------------------------
    (("-1.00", []), {}, ("raises", "ValueError")),
    (("", []), {}, ("raises", "ValueError")),
    (("1e3", []), {}, ("raises", "ValueError")),
    ((100.0, []), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "percent", "value": "100.01"}]), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "bogo", "value": "10"}]), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "amount", "value": "-1.00"}]), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "percent"}]), {}, ("raises", "ValueError")),
    # --- validation still happens after the clamp (SPEC, "Validation is
    #     unconditional") ------------------------------------------------
    (("10.00", [{"kind": "amount", "value": "15.00"},
                {"kind": "bogo", "value": "1"}]), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "amount", "value": "15.00"},
                {"kind": "percent", "value": "101"}]), {}, ("raises", "ValueError")),

    # ---------------------------------------------------------------------
    # REFERENCE DEFECTS.  These are expected to FAIL against reference.py.
    # They are kept in KNOWN_VALUES on purpose so the harness prints them.
    # ---------------------------------------------------------------------
    # (b1) SPEC "Money representation": the grammar is "an optional '-', then
    #      one or more digits, then optionally a '.' followed by one or more
    #      digits.  Nothing else: no '+' sign, no thousands separator, NO
    #      WHITESPACE, no exponent, no empty string."  A trailing newline is
    #      whitespace and is not in the grammar, so it is malformed.
    #      reference.py anchors its regex with '$' instead of '\\Z' (or
    #      re.fullmatch), and '$' matches immediately before a trailing
    #      newline, so exactly one trailing '\\n' is silently accepted -- on
    #      the subtotal AND on discount values of both kinds.
    (("5.00\n", []), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "percent", "value": "10\n"}]), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "amount", "value": "1.00\n"}]), {}, ("raises", "ValueError")),
    # (b2) Same clause: "digits" in a decimal money grammar means [0-9].
    #      reference.py uses '\\d', which under Unicode matches every Nd
    #      character, so Arabic-Indic (U+0660..), fullwidth (U+FF10..) and
    #      Tibetan (U+0F20..) digits are accepted as money and parsed by
    #      Decimal.  "٥.٠٠" is accepted and returns "5.00".
    (("٥.٠٠", []), {}, ("raises", "ValueError")),
    (("５.００", []), {}, ("raises", "ValueError")),
    (("10.00", [{"kind": "percent", "value": "٥"}]), {}, ("raises", "ValueError")),
]
