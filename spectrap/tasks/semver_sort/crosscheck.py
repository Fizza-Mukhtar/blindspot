"""Independent oracle for RELENG-412 (semver_sort).

Deliberately structured differently from the obvious "build a sort key tuple and
call list.sort" implementation:

  * validation is a hand-written recursive-descent / character-scanning parser
    transcribed directly from the SemVer 2.0.0 BNF grammar (no regex at all);
  * ordering is an explicit *pairwise* comparator that transcribes clauses
    11.2, 11.3, 11.4.1, 11.4.2, 11.4.3 and 11.4.4 as a literal decision table;
  * the sort itself is a hand-rolled O(n^2) binary-free insertion sort that
    scans from the right and inserts *after* the last element of equal-or-lower
    precedence, which makes stability a property of the algorithm rather than
    something inherited from CPython's Timsort.
"""

from __future__ import annotations

ORACLE_NOTES = (
    "Based on SemVer 2.0.0 (semver.org/spec/v2.0.0.html). Validation is a "
    "hand-written character scan transcribed from the spec's own BNF (no "
    "regex); ordering is a pairwise comparator transcribing 11.1/11.2/11.3/"
    "11.4.1/11.4.2/11.4.3/11.4.4 as a decision table; the sort is a hand-rolled "
    "stable insertion sort so stability is not inherited from Timsort. "
    "Asymmetry the BNF makes explicit and SPEC.md never mentions: a <build "
    "identifier> may be <digits>, so leading zeroes ARE legal in build "
    "metadata (item 10's own example is 1.0.0-alpha+001), while a numeric "
    "<pre-release identifier> may not have them (item 9). Any implementation "
    "reusing one identifier validator for both parts wrongly rejects "
    "1.0.0+001. Other notes: the leading 'v' is not in the standard at all "
    "(v1.2.3 is not valid semver per the BNF) -- a local extension of the "
    "ticket; I accept exactly one optional lowercase 'v'. SPEC.md does not "
    "determine which tag is named when several are invalid; I raise on the "
    "first in input order. SPEC.md rule 3's 'containing a letter or a hyphen' "
    "is equivalent to the BNF's <alphanumeric identifier>, but the test that "
    "actually matters is 'all digits' vs 'not all digits'."
)

_DIGITS = frozenset("0123456789")
_NON_DIGIT = frozenset(
    "-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)
_IDENT_CHARS = _DIGITS | _NON_DIGIT


# ---------------------------------------------------------------------------
# Grammar, transcribed from the SemVer 2.0.0 BNF.
# ---------------------------------------------------------------------------

def _is_digits(s):
    """<digits> ::= <digit> | <digit> <digits>  (leading zeroes allowed)"""
    if not s:
        return False
    for ch in s:
        if ch not in _DIGITS:
            return False
    return True


def _is_numeric_identifier(s):
    """<numeric identifier> ::= "0" | <positive digit> | <positive digit> <digits>"""
    if not _is_digits(s):
        return False
    if s == "0":
        return True
    return s[0] != "0"


def _is_alphanumeric_identifier(s):
    """<alphanumeric identifier> — identifier chars only, at least one non-digit."""
    if not s:
        return False
    saw_non_digit = False
    for ch in s:
        if ch not in _IDENT_CHARS:
            return False
        if ch in _NON_DIGIT:
            saw_non_digit = True
    return saw_non_digit


def _is_prerelease_identifier(s):
    """<pre-release identifier> ::= <alphanumeric identifier> | <numeric identifier>"""
    return _is_alphanumeric_identifier(s) or _is_numeric_identifier(s)


def _is_build_identifier(s):
    """<build identifier> ::= <alphanumeric identifier> | <digits>

    NB: <digits>, not <numeric identifier> — leading zeroes are legal here.
    """
    return _is_alphanumeric_identifier(s) or _is_digits(s)


def _parse(tag):
    """Parse one tag into (core, prerelease_identifiers) or return None.

    Scans the string character by character rather than matching a regex.
    """
    if not isinstance(tag, str):
        return None

    s = tag
    # Local extension of the ticket: one optional decorative leading "v".
    if s[:1] == "v":
        s = s[1:]

    # Split off build metadata at the FIRST "+" (a "+" may not appear inside
    # any identifier, so the first one is the delimiter).
    plus = s.find("+")
    if plus >= 0:
        build = s[plus + 1:]
        s = s[:plus]
        parts = build.split(".")
        for ident in parts:
            if not _is_build_identifier(ident):
                return None

    # Split off pre-release at the FIRST "-" that follows the version core.
    # The core contains only digits and dots, so the first "-" in what remains
    # is unambiguously the pre-release delimiter (hyphens inside pre-release
    # identifiers are legal but come after it).
    hyphen = s.find("-")
    if hyphen >= 0:
        pre = s[hyphen + 1:]
        s = s[:hyphen]
        pre_ids = pre.split(".")
        for ident in pre_ids:
            if not _is_prerelease_identifier(ident):
                return None
    else:
        pre_ids = []

    core_parts = s.split(".")
    if len(core_parts) != 3:
        return None
    for part in core_parts:
        if not _is_numeric_identifier(part):
            return None

    core = (int(core_parts[0]), int(core_parts[1]), int(core_parts[2]))
    return core, pre_ids


# ---------------------------------------------------------------------------
# Precedence, as an explicit decision table over clauses 11.2 - 11.4.4.
# ---------------------------------------------------------------------------

def _cmp_identifier(a, b):
    a_num = _is_digits(a)
    b_num = _is_digits(b)
    if a_num and b_num:
        # 11.4.1 identifiers consisting of only digits are compared numerically
        ia, ib = int(a), int(b)
        return -1 if ia < ib else (1 if ia > ib else 0)
    if a_num and not b_num:
        # 11.4.3 numeric identifiers always have lower precedence
        return -1
    if b_num and not a_num:
        return 1
    # 11.4.2 identifiers with letters or hyphens compare lexically in ASCII order
    return -1 if a < b else (1 if a > b else 0)


def _cmp_version(x, y):
    (xc, xp), (yc, yp) = x, y

    # 11.2 major, minor, patch compared numerically, first difference wins
    for i in range(3):
        if xc[i] != yc[i]:
            return -1 if xc[i] < yc[i] else 1

    # 11.3 a pre-release version has lower precedence than a normal version
    if xp and not yp:
        return -1
    if yp and not xp:
        return 1
    if not xp and not yp:
        return 0

    # 11.4 compare dot separated identifiers left to right
    n = min(len(xp), len(yp))
    for i in range(n):
        c = _cmp_identifier(xp[i], yp[i])
        if c:
            return c

    # 11.4.4 a larger set of pre-release fields has higher precedence
    if len(xp) != len(yp):
        return -1 if len(xp) < len(yp) else 1

    # 11.1 build metadata never reached this comparator -> equal precedence
    return 0


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def oracle(tags):
    return sort_versions(tags)


def sort_versions(tags):
    parsed = []
    for tag in tags:
        p = _parse(tag)
        if p is None:
            raise ValueError(tag)
        parsed.append((tag, p))

    # Stable insertion sort: scan right-to-left and insert after the last
    # element whose precedence is <= the incoming one, so ties keep input order.
    out = []
    for item in parsed:
        j = len(out)
        while j > 0 and _cmp_version(out[j - 1][1], item[1]) > 0:
            j -= 1
        out.insert(j, item)
    return [tag for tag, _ in out]


# ---------------------------------------------------------------------------
# Values derived from the standard's own worked examples.
# ---------------------------------------------------------------------------

KNOWN_VALUES = [
    # empty input
    (([],), {}, []),

    # 11.2's own example: 1.0.0 < 2.0.0 < 2.1.0 < 2.1.1
    ((["2.1.0", "1.0.0", "2.1.1", "2.0.0"],), {},
     ["1.0.0", "2.0.0", "2.1.0", "2.1.1"]),

    # 11.3's own example: 1.0.0-alpha < 1.0.0
    ((["1.0.0", "1.0.0-alpha"],), {}, ["1.0.0-alpha", "1.0.0"]),

    # 11.4's own example, in full, fed in reverse
    ((["1.0.0", "1.0.0-rc.1", "1.0.0-beta.11", "1.0.0-beta.2", "1.0.0-beta",
       "1.0.0-alpha.beta", "1.0.0-alpha.1", "1.0.0-alpha"],), {},
     ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
      "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]),

    # 11.4.1 numeric identifiers compare numerically, not lexically
    ((["1.0.0-rc.10", "1.0.0-rc.2"],), {}, ["1.0.0-rc.2", "1.0.0-rc.10"]),

    # 11.4.3 an all-digit identifier ranks below an alphanumeric one
    ((["1.0.0-alpha.beta", "1.0.0-alpha.11"],), {},
     ["1.0.0-alpha.11", "1.0.0-alpha.beta"]),

    # 11.4.4 the larger identifier set wins on an equal prefix
    ((["1.0.0-alpha.1", "1.0.0-alpha"],), {}, ["1.0.0-alpha", "1.0.0-alpha.1"]),

    # item 10 / 11.1: build metadata ignored -> equal precedence -> stable tie
    ((["1.0.0+build.99", "1.0.0+build.1", "1.0.0"],), {},
     ["1.0.0+build.99", "1.0.0+build.1", "1.0.0"]),

    # item 10's own examples are valid versions, including a leading-zero build
    # identifier ("1.0.0-alpha+001") which the BNF allows via <digits>.
    ((["1.0.0+20130313144700", "1.0.0-beta+exp.sha.5114f85", "1.0.0-alpha+001"],), {},
     ["1.0.0-alpha+001", "1.0.0-beta+exp.sha.5114f85", "1.0.0+20130313144700"]),

    # item 9's own pre-release examples
    ((["1.0.0-x.7.z.92", "1.0.0-x-y-z.--", "1.0.0-0.3.7", "1.0.0-alpha.1",
       "1.0.0-alpha.beta"],), {},
     # "x" is a proper ASCII prefix of "x-y-z", so x.7.z.92 sorts first (11.4.2)
     ["1.0.0-0.3.7", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-x.7.z.92",
      "1.0.0-x-y-z.--"]),

    # 11.4.2 ASCII sort order: uppercase letters sort before lowercase
    ((["1.0.0-a", "1.0.0-A"],), {}, ["1.0.0-A", "1.0.0-a"]),

    # decorative "v" is ignored for ordering but preserved in the output
    ((["v2.0.0", "1.10.0", "1.9.0"],), {}, ["1.9.0", "1.10.0", "v2.0.0"]),

    # invalid: leading zero in a numeric core identifier (item 2 / BNF)
    ((["1.01.0"],), {}, ("raises", "ValueError")),
    # invalid: leading zero in a numeric pre-release identifier (item 9)
    ((["1.0.0-01"],), {}, ("raises", "ValueError")),
    # invalid: empty pre-release identifier (item 9)
    ((["1.0.0-"],), {}, ("raises", "ValueError")),
    ((["1.0.0-a..b"],), {}, ("raises", "ValueError")),
    # invalid: version core is not three parts (BNF)
    ((["1.0"],), {}, ("raises", "ValueError")),
    # invalid: empty build identifier (item 10)
    ((["1.0.0+"],), {}, ("raises", "ValueError")),
    # invalid: "_" is not an identifier character (BNF)
    ((["1.0.0-al_pha"],), {}, ("raises", "ValueError")),

    # --- second batch: corners the generator never reaches -------------------

    # <build identifier> ::= <alphanumeric identifier> | <digits>
    # <digits> permits leading zeroes, so these are VALID (contrast the
    # pre-release cases just below, which are not).
    ((["1.2.3+0123"],), {}, ["1.2.3+0123"]),
    ((["1.0.0+001", "1.0.0"],), {}, ["1.0.0+001", "1.0.0"]),
    # ... while a numeric <pre-release identifier> may not (item 9)
    ((["1.2.3-0123"],), {}, ("raises", "ValueError")),
    ((["1.0.0-00"],), {}, ("raises", "ValueError")),
    # "0" alone is a legal <numeric identifier>
    ((["1.0.0-0"],), {}, ["1.0.0-0"]),
    ((["0.0.0"],), {}, ["0.0.0"]),
    # leading zero in the major component
    ((["01.0.0"],), {}, ("raises", "ValueError")),
    # empty <build identifier> (item 10: identifiers "MUST NOT be empty")
    ((["1.0.0+a..b"],), {}, ("raises", "ValueError")),

    # 11.4.3 at the first identifier: numeric ranks below alphanumeric
    ((["1.0.0-alpha", "1.0.0-1"],), {}, ["1.0.0-1", "1.0.0-alpha"]),
    # 11.4.1 vs a naive lexical compare
    ((["1.0.0-2", "1.0.0-11"],), {}, ["1.0.0-2", "1.0.0-11"]),
    # "-" is a <non-digit>, so "-" is an <alphanumeric identifier> and 11.4.3
    # puts the numeric "1" below it
    ((["1.0.0-alpha.-", "1.0.0-alpha.1"],), {},
     ["1.0.0-alpha.1", "1.0.0-alpha.-"]),
    # 11.4.4 again, three identifiers vs two
    ((["1.0.0-alpha.beta.1", "1.0.0-alpha.beta"],), {},
     ["1.0.0-alpha.beta", "1.0.0-alpha.beta.1"]),
    # 11.1: build metadata excluded even when a pre-release is present ->
    # equal precedence -> input order preserved
    ((["1.0.0-rc.1+build.2", "1.0.0-rc.1+build.1", "v1.0.0-rc.1"],), {},
     ["1.0.0-rc.1+build.2", "1.0.0-rc.1+build.1", "v1.0.0-rc.1"]),
    # item 2: major/minor/patch are non-negative integers with no stated bound
    ((["1.0.0", "99999999999999999999.0.0", "2.0.0"],), {},
     ["1.0.0", "2.0.0", "99999999999999999999.0.0"]),
]

# --- third batch: prefix / delimiter corners (all standard-derivable) --------
KNOWN_VALUES += [
    # The BNF has no "v" at all; SPEC.md licenses exactly a lowercase leading
    # "v" and nothing else.
    ((["V1.0.0"],), {}, ("raises", "ValueError")),
    ((["vv1.0.0"],), {}, ("raises", "ValueError")),
    ((["=1.0.0"],), {}, ("raises", "ValueError")),
    (([" 1.0.0"],), {}, ("raises", "ValueError")),
    ((["1.0.0 "],), {}, ("raises", "ValueError")),
    # empty <build> after the "+"
    ((["1.0.0-alpha+"],), {}, ("raises", "ValueError")),
    # "-" alone is a legal <alphanumeric identifier> in build metadata too
    ((["1.0.0+-"],), {}, ["1.0.0+-"]),
    # four-component core is not a <version core>
    ((["1.0.0.0"],), {}, ("raises", "ValueError")),
    # "0A" is alphanumeric (has a non-digit) so the leading-zero rule for
    # <numeric identifier> does not apply
    ((["1.0.0-0A"],), {}, ["1.0.0-0A"]),
    # 11.4.2 ASCII: "Alpha" (0x41) before "alpha" (0x61)
    ((["1.0.0-alpha", "1.0.0-Alpha"],), {}, ["1.0.0-Alpha", "1.0.0-alpha"]),
    # 11.4.3 at a later position: numeric "2" below alphanumeric "beta"
    ((["1.0.0-alpha.1.beta", "1.0.0-alpha.1.2"],), {},
     ["1.0.0-alpha.1.2", "1.0.0-alpha.1.beta"]),
]
