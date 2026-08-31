# PAY-2291 — Quantise a monetary amount to its currency's minor units

**Component:** `payments/formatting`
**Reporter:** Tomás (Payments Platform)

## Background

The settlement file writer formats every amount with `"%.2f"` and that is wrong
for a growing share of our corridors — our Tokyo acquirer rejects a whole batch
when a JPY line arrives as `1234.00`, and Kuwait and Bahrain go the other way,
so writing `1.235` as `1.23` loses a fils a line and reconciliation drifts by a
few dinars a day. Separately, someone "simplified" the invoice renderer to
`round(float(amount), 2)` last quarter and `2.675` came out as `2.67`, because
that value is not representable in binary floating point. One function, exact
decimal arithmetic, called by both writers and shortly by the ledger export.

## What to build

```python
def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    ...
```

`exponents` maps an ISO 4217 alphabetic currency code to that currency's number
of minor units — the "exponent" column of the standard
(<https://www.iso.org/iso-4217-currency-codes.html>). The caller owns the table
and passes it in, so this stays pure and reads no data file. Look the code up
exactly as given, with no upper-casing, trimming or aliasing, and raise
`KeyError` when it is not a key of the table; do that lookup before you go
anywhere near the amount, so a call carrying both an unknown code and a junk
amount comes back as a `KeyError` rather than a `ValueError`. Read the exponent
for the currency you were handed and emit that many decimals — the yen has no
minor unit at all, the Gulf currencies are quoted in thousandths and CLF in
ten-thousandths — so never assume two.

`amount` goes to `decimal.Decimal` unchanged: any string it accepts as a finite
number is valid input, which covers an explicit sign, scientific notation
(`"1E+2"`, `"-1.5e-3"`), more or fewer decimals than the target, and
surrounding whitespace, with no bound on magnitude. Build the value from the
string; a detour through `float` destroys precisely the halfway cases this
ticket exists for. A literal `decimal` rejects surfaces as
`decimal.InvalidOperation`, an `ArithmeticError` rather than a `ValueError`, so
translate it: anything unparseable (`""`, `"abc"`, `"1.2.3"`, `"12,34"`,
`"$1.00"`, `"1 000.00"`) or non-finite (`"NaN"`, `"sNaN"`, `"Infinity"`,
`"-Infinity"`) must raise `ValueError`.

Quantise to that many decimals under `decimal.ROUND_HALF_EVEN`
(<https://docs.python.org/3/library/decimal.html#decimal.ROUND_HALF_EVEN>),
which is what our ledger and both acquirers use — so in USD `"2.675"` is `2.68`
while `"2.665"` is `2.66` — and negatives round symmetrically on the magnitude
and keep their sign.

Return a plain positional decimal string with exactly that many digits after
the point, zero-padded when the input had fewer, no thousands separators, no
symbol or code, no exponent notation however large the number, and no leading
`+`. Where the exponent is `0` there is no fractional part and therefore no
decimal point either, so `"1234.5"` in JPY is `"1234"` — never `"1234."` and
never `"1234.0"`. Zero is written unsigned even when it was reached from below:
`"-0.004"` in USD is `"0.00"`, and `"-0.4"` in JPY is `"0"`.

## Out of scope

- Checking that a code in `exponents` is a real ISO 4217 code, or that its
  exponent matches the published table. The caller's table is authoritative.
- Currency conversion, symbols, locale-aware grouping, and accounting
  negatives such as `(1.00)`.
- Any caching or persistence. The function is pure.
