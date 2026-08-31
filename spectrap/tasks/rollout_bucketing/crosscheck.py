"""Independent oracle for FLAG-238 (rollout_bucketing / is_enabled).

Deliberately does NOT call hashlib.  The digest is re-implemented from
FIPS PUB 180-4 section 6.2 (SHA-256) so that the oracle shares no code path
with the reference, and the modulo-100 reduction is done by Horner's method
over the 32 digest bytes rather than by parsing a hex string into a bignum.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# SHA-256, transcribed from FIPS PUB 180-4.
#   4.1.2  -- Ch, Maj, Sigma0, Sigma1, sigma0, sigma1
#   4.2.2  -- the 64 constants K[t] (cube roots of the first 64 primes)
#   5.1.1  -- padding: append 0x80, then zeros, then the 64-bit big-endian
#             message length in bits, so that len % 64 == 0
#   5.3.3  -- the eight initial hash values H(0) (square roots of the first
#             eight primes)
#   6.2.2  -- the message schedule and the 64-round compression function
# --------------------------------------------------------------------------

_K = (
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
    0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
    0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
    0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
    0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
    0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
    0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
    0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
)

_H0 = (
    0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A,
    0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19,
)

_MASK = 0xFFFFFFFF


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & _MASK


def _sha256(message: bytes) -> bytes:
    """SHA-256 of ``message``, per FIPS 180-4.  Returns the 32-byte digest."""
    # 5.1.1 padding
    bit_len = len(message) * 8
    padded = bytearray(message)
    padded.append(0x80)
    while len(padded) % 64 != 56:
        padded.append(0x00)
    padded += bit_len.to_bytes(8, "big")

    h = list(_H0)

    for off in range(0, len(padded), 64):
        block = padded[off:off + 64]

        # 6.2.2 step 1: the message schedule
        w = [int.from_bytes(block[i * 4:i * 4 + 4], "big") for i in range(16)]
        for t in range(16, 64):
            s0 = _rotr(w[t - 15], 7) ^ _rotr(w[t - 15], 18) ^ (w[t - 15] >> 3)
            s1 = _rotr(w[t - 2], 17) ^ _rotr(w[t - 2], 19) ^ (w[t - 2] >> 10)
            w.append((w[t - 16] + s0 + w[t - 7] + s1) & _MASK)

        # 6.2.2 step 2
        a, b, c, d, e, f, g, hh = h

        # 6.2.2 step 3
        for t in range(64):
            S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = (e & f) ^ (~e & g)
            t1 = (hh + S1 + ch + _K[t] + w[t]) & _MASK
            S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = (S0 + maj) & _MASK
            hh = g
            g = f
            f = e
            e = (d + t1) & _MASK
            d = c
            c = b
            b = a
            a = (t1 + t2) & _MASK

        # 6.2.2 step 4
        h = [(x + y) & _MASK for x, y in zip(h, (a, b, c, d, e, f, g, hh))]

    return b"".join(x.to_bytes(4, "big") for x in h)


# Self-check against the NIST worked examples so a typo in the transcription
# above cannot silently masquerade as a reference bug.
assert _sha256(b"abc").hex() == (
    "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
)
assert _sha256(b"").hex() == (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
assert _sha256(
    b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
).hex() == (
    "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
)


def _bucket(flag_key: str, user_id: str) -> int:
    """Bucket 0..99 for a pair.

    Different structure from the ticket's one-liner: the digest bytes are
    reduced modulo 100 by Horner's method instead of being parsed out of a
    hex string as a single bignum.  Mathematically identical, textually
    unrelated.
    """
    digest = _sha256((flag_key + ":" + user_id).encode("utf-8"))
    acc = 0
    for byte in digest:
        acc = (acc * 256 + byte) % 100
    return acc


# --------------------------------------------------------------------------
# Validation, expressed as an explicit ordered decision table rather than a
# chain of ifs, so the "types first, then range" ordering is visible.
# --------------------------------------------------------------------------

_RULES = (
    # (predicate on (flag_key, user_id, percentage), exception to raise)
    (lambda k, u, p: not isinstance(k, str), TypeError),
    (lambda k, u, p: not isinstance(u, str), TypeError),
    (lambda k, u, p: isinstance(p, bool), TypeError),
    (lambda k, u, p: not isinstance(p, int), TypeError),
    (lambda k, u, p: p < 0 or p > 100, ValueError),
)


def oracle(flag_key, user_id, percentage):
    for predicate, exc in _RULES:
        if predicate(flag_key, user_id, percentage):
            raise exc(
                "flag_key=%r user_id=%r percentage=%r" % (flag_key, user_id, percentage)
            )

    # Brute force the rule as literally stated: enumerate the 100 buckets and
    # ask which of them are admitted at this percentage.
    admitted = frozenset(b for b in range(100) if b < percentage)
    return bool(_bucket(flag_key, user_id) in admitted)


ORACLE_NOTES = """\
Oracle basis
------------
The digest is a from-scratch transcription of SHA-256 out of FIPS PUB 180-4
(sections 4.1.2, 4.2.2, 5.1.1, 5.3.3, 6.2.2).  hashlib is deliberately NOT
used, so the oracle and the reference share no digest code.  The
transcription is pinned at import time against the three NIST worked
examples: SHA-256("abc"), SHA-256(""), and the 448-bit two-block example
"abcdbcde...nopq".

Structural divergences from the ticket's one-liner, on purpose:
  * modulo 100 is done by Horner's method over the 32 digest bytes, not by
    int(hexdigest, 16);
  * "bucket < percentage" is evaluated by materialising the admitted bucket
    set frozenset(b for b in range(100) if b < percentage) and testing
    membership, so an off-by-one in the threshold cannot hide behind a
    shared comparison operator;
  * validation is an ordered decision table, which makes the ticket's
    "types before range" ordering, and the bool-before-int check, explicit.

Clauses checked
---------------
  * FIPS 180-4 5.1.1 / 6.2 -- padding and compression, verified against the
    standard's own worked examples (Appendix B).
  * PYTHONHASHSEED (Python docs, using/cmdline): str/bytes hash() is salted
    per process unless the seed is pinned, so builtin hash() cannot be the
    bucket source.  Nothing in the oracle touches hash().
  * SPEC "The bucketing rule" 1-4: material is exactly f"{flag_key}:{user_id}",
    UTF-8, SHA-256, big-endian unsigned, mod 100, strict "<".
  * SPEC "Monotonicity": satisfied structurally -- percentage is not an
    input to _bucket at all, and the admitted set is monotonically
    increasing in percentage by construction.
  * SPEC "Percentage boundaries": p=0 -> empty admitted set -> everyone off;
    p=100 -> all 100 buckets admitted -> everyone on.
  * SPEC "Errors": bool rejected before the int check; float (even integral)
    rejected; types before range.

Ambiguities / concerns
----------------------
1. The cited grounding URL (the Unleash gradual-rollout post) does not
   actually describe THIS algorithm.  Unleash's flexible-rollout strategy
   uses MurmurHash3 of "groupId:userId", normalised to 1..100, and compares
   normalisedValue <= rollout.  The ticket pins SHA-256, buckets 0..99, and
   a strict "<".  Both schemes are internally consistent and both are
   monotonic, but they are not the same scheme and they disagree on which
   users are in the 1% cohort.  Only the property the blog post is cited
   for -- "do not fold the percentage into the hash material" -- transfers.
   The ticket is self-contained and unambiguous, so this is a grounding-link
   mismatch, not a defect in the ticket.
2. Under-determined: the ticket never says what happens when flag_key
   itself contains ':'.  ("a:b", "c") and ("a", "b:c") both produce the
   material "a:b:c" and therefore collide onto the same bucket.  The oracle
   follows the pinned formula and lets them collide.
3. Under-determined: 2**256 is not a multiple of 100, so the buckets are
   not exactly equiprobable (buckets 0..35 are very slightly favoured).
   The ticket pins the formula without saying whether that bias is
   accepted.  The oracle reproduces it.
4. Not stated: whether int subclasses other than bool (e.g. IntEnum) are
   acceptable percentages.  The oracle accepts them, since the ticket
   carves out bool specifically and nothing else.
5. Not stated: which of flag_key / user_id is reported first when both are
   non-str.  Immaterial -- both raise TypeError.
"""


# Expected values below are derived from the ticket's own worked examples
# where it gives them, and otherwise from the FIPS-180-4 digest computed by
# the transcription above (cross-checked against the standard's test
# vectors), never from the reference.
KNOWN_VALUES: list[tuple[tuple, dict, object]] = [
    # --- the ticket's own worked examples -------------------------------
    # "checkout-v2:user-1042" -> bucket 19
    (("checkout-v2", "user-1042", 19), {}, False),   # 19 is not < 19
    (("checkout-v2", "user-1042", 20), {}, True),    # 19 < 20
    (("checkout-v2", "user-1042", 0), {}, False),
    (("checkout-v2", "user-1042", 100), {}, True),
    # "search-rerank:user-1042" -> bucket 10, "already enabled at 11%"
    (("search-rerank", "user-1042", 11), {}, True),
    (("search-rerank", "user-1042", 10), {}, False),
    # ":" -> bucket 35; the ticket states is_enabled("", "", 36) is True
    (("", "", 36), {}, True),
    (("", "", 35), {}, False),

    # --- boundary extremes ----------------------------------------------
    (("new-nav", "user-0", 0), {}, False),           # 0 disables everyone
    (("new-nav", "user-0", 100), {}, True),          # 100 enables everyone
    (("billing-retry", "user-42", 0), {}, False),
    (("billing-retry", "user-42", 100), {}, True),

    # --- separator collision (material "a:b:c" both ways) ---------------
    # SHA-256("a:b:c") reduces to bucket 6, so both halves flip at 7.
    (("a:b", "c", 6), {}, False),
    (("a:b", "c", 7), {}, True),
    (("a", "b:c", 6), {}, False),
    (("a", "b:c", 7), {}, True),

    # --- UTF-8 material --------------------------------------------------
    # "billing-retry:üser-é☃" -> bucket 54
    (("billing-retry", "üser-é☃", 54), {}, False),
    (("billing-retry", "üser-é☃", 55), {}, True),

    # --- errors: types first, then range ---------------------------------
    (("f", "u", 101), {}, ("raises", "ValueError")),
    (("f", "u", -1), {}, ("raises", "ValueError")),
    (("f", "u", 50.0), {}, ("raises", "TypeError")),
    (("f", "u", 101.0), {}, ("raises", "TypeError")),   # type wins over range
    (("f", "u", True), {}, ("raises", "TypeError")),
    (("f", "u", False), {}, ("raises", "TypeError")),
    (("f", "u", "50"), {}, ("raises", "TypeError")),
    (("f", "u", None), {}, ("raises", "TypeError")),
    ((None, "u", 50), {}, ("raises", "TypeError")),
    ((b"f", "u", 50), {}, ("raises", "TypeError")),
    (("f", 42, 50), {}, ("raises", "TypeError")),
    (("f", ["u"], 50), {}, ("raises", "TypeError")),
]
