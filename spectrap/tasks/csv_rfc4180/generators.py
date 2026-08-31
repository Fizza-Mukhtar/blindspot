"""Deterministic input generator for differential fuzzing of DATAX-238.

The forge calls ``sample(rng)`` many times, runs the candidate and the
reference on each input, and keeps the first input where they disagree.

Uniform random text would essentially never produce a field that contains a
double quote adjacent to a comma, or a lone carriage return, or a value made
entirely of spaces -- and those are precisely the fields where RFC 4180's
quoting rules bite.  So the alphabet here is a hand-built pool of "boring"
values mixed with the quote-triggering ones, plus a composition step that
concatenates a padded prefix onto a trigger so that combinations such as
``'  a,b  '`` (quoted, but with its padding untouched) show up often.  Widths
include zero so that empty records appear, and a small minority of samples has
one field replaced by a non-``str`` value, which must raise ``TypeError``.
"""

from __future__ import annotations

import random

# Values with no quote trigger at all: these must come out verbatim.
PLAIN = [
    "a",
    "b",
    "id",
    "42",
    "0041",
    "priya",
    "hello world",
    "naïve",
    "x-y",
    "3.14",
    "semi;colon",
    "tab\there",
    "hash#mark",
    "back\\slash",
    "'single'",
]

# Whitespace that is data, never a quote trigger and never trimmed.
SPACED = [
    " ",
    "   ",
    " lead",
    "trail ",
    "  both  ",
    "\t",
    " \t ",
]

# Comma and double-quote triggers, including the adjacency cases.
SPECIAL = [
    ",",
    ",,",
    "a,b",
    "a,b,c",
    '"',
    '""',
    '"quoted"',
    'a"b',
    'He said "hi"',
    '"leading',
    'trailing"',
    '","',
    'a,"b",c',
]

# Line-break triggers: full CRLF, and the lone CR / lone LF corner.
LINEBREAK = [
    "\r\n",
    "\n",
    "\r",
    "a\r\nb",
    "a\nb",
    "a\rb",
    "end\r\n",
    "\n\r",
    "multi\r\nline\r\nfield",
]

# Non-string field values, every one of which must raise TypeError.
NON_STR = [0, 1, 42, None, True, False, 3.5, b"bytes", ["nested"], ("t",), {"k": 1}]


def _atom(rng: random.Random) -> str:
    r = rng.random()
    if r < 0.26:
        return rng.choice(PLAIN)
    if r < 0.42:
        return ""  # the empty field: written as nothing at all
    if r < 0.60:
        return rng.choice(SPACED)
    if r < 0.84:
        return rng.choice(SPECIAL)
    return rng.choice(LINEBREAK)


def _field(rng: random.Random) -> str:
    """One field, sometimes a concatenation so triggers meet padding."""
    value = _atom(rng)
    if rng.random() < 0.30:
        value = value + _atom(rng)
    if rng.random() < 0.15:
        value = " " + value + "  "  # padding must survive, quoted or not
    return value


def sample(rng: random.Random) -> tuple[tuple, dict]:
    n_rows = rng.randint(0, 5)
    rows: list[list] = []
    for _ in range(n_rows):
        # Widths are deliberately ragged, and 0 is included.
        width = rng.choice([0, 1, 1, 2, 2, 2, 3, 3, 4, 5])
        rows.append([_field(rng) for _ in range(width)])

    if rng.random() < 0.15:
        positions = [
            (i, j) for i, row in enumerate(rows) for j in range(len(row))
        ]
        if positions:
            i, j = rng.choice(positions)
            rows[i][j] = rng.choice(NON_STR)

    return (rows,), {}


# Tried before random sampling.  These encode the corners the RFC and the
# ticket call out by name.
SEEDS: list[tuple[tuple, dict]] = [
    (([],), {}),                                    # empty table -> ""
    (([[]],), {}),                                  # zero-field record -> bare CRLF
    (([["a", "b", "c"]],), {}),                     # clause 4: comma separated
    (([['He said "hi"']],), {}),                    # clause 7: doubled quote
    (([['"']],), {}),                               # single quote -> """"
    (([["Portland, OR"]],), {}),                    # clause 6: embedded comma
    (([["  keep  my  spaces  "], ["   "]],), {}),   # clause 4: spaces are data
    (([[""]],), {}),                                # empty field -> nothing
    (([["", "", ""]],), {}),                        # -> ",,"
    (([["line1\r\nline2"]],), {}),                  # embedded CRLF
    (([["lone\rcr"], ["lone\nlf"], ["\r"], ["\n"]],), {}),  # lone CR / lone LF
    (([["a"], ["b", "c"], [], ["d", "e", "f"]],), {}),      # ragged records
    (([["semi;colon\ttab#hash"]],), {}),            # non-triggers stay unquoted
    (([["a", 1]],), {}),                            # invalid: int field
    (([["ok"], [None]],), {}),                      # invalid: None field
    (([[b"bytes"]],), {}),                          # invalid: bytes field
]
