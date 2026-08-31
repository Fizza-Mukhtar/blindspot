# PAY-2291 — Quantise a monetary amount to its currency's minor units

**Component:** `payments/formatting`
**Reporter:** Tomás (Payments Platform)
**Consumers:** the settlement file writer, the invoice PDF renderer, the ledger export

## Background

The settlement file writer currently formats every amount with `"%.2f"`. That is
wrong for a growing share of our corridors. Our Tokyo acquirer rejects a whole
batch when a JPY line arrives as `1234.00`, because the yen has no minor unit at
all and the file grammar allows only whole yen. Kuwait and Bahrain go the other
way: KWD and BHD are quoted in thousandths, so writing `1.235` as `1.23` quietly
loses a fils per line, and reconciliation drifts by a few dinars a day.

We also had a nastier incident last quarter. Someone "simplified" the invoice
renderer to `round(float(amount), 2)`. Because `2.675` is not representable in
binary floating point, it stored as slightly *less* than 2.675 and rounded down
to `2.67`. Finance noticed because the same batch also contained `2.665`, which
is *supposed* to round down, and the two lines disagreed with the ledger in
opposite directions. We want one function that both writers call, and we want
the rounding done in exact decimal arithmetic.

## What to build

```python
def format_amount(amount: str, currency: str, exponents: dict[str, int]) -> str:
    ...
```

`exponents` maps an ISO 4217 alphabetic currency code to that currency's number
of minor units — the "exponent" column of the standard
(<https://www.iso.org/iso-4217-currency-codes.html>). The caller owns that table
and passes it in, so this function stays pure and reads no data file. Look the
code up **exactly as given**: no upper-casing, no trimming, no aliasing.

The exponent is **not always 2.** The table we ship today contains, among
others, `USD: 2`, `EUR: 2`, `JPY: 0`, `ISK: 0`, `UGX: 0`, `KWD: 3`, `BHD: 3`,
`OMR: 3`, `TND: 3`, and `CLF: 4`. Read the exponent for the currency you were
handed and use that number of decimals; never assume two.

## Accepted input

`amount` is a decimal string. Hand it to `decimal.Decimal` unchanged: **any
string `decimal.Decimal` accepts as a finite number is valid input here.** That
includes an explicit sign (`"+1.5"`, `"-7"`), scientific notation (`"1E+2"`,
`"-1.5e-3"`), an amount with more decimals than the target (`"1.23456"`), one
with fewer or none (`"5"`), and a string with surrounding whitespace
(`"  1.5  "`). There is no bound on magnitude.

`"NaN"`, `"sNaN"`, `"Infinity"` and `"-Infinity"` parse as `Decimal` but are not
finite numbers and are **not** valid amounts here.

## Rounding

Round the parsed value to the currency's exponent using **half-even rounding**
(`decimal.ROUND_HALF_EVEN`,
<https://docs.python.org/3/library/decimal.html#decimal.ROUND_HALF_EVEN>), which
is what our ledger and both acquirers use. A value exactly half way between two
representable amounts goes to the neighbour whose last kept digit is **even**:

| amount     | currency | result  | why                                    |
| ---------- | -------- | ------- | -------------------------------------- |
| `"2.675"`  | USD (2)  | `2.68`  | tie; `7` is odd, so go up to `8`       |
| `"2.665"`  | USD (2)  | `2.66`  | tie; `6` is already even, so stay      |
| `"8.835"`  | USD (2)  | `8.84`  | tie; `3` is odd, so go up to `4`       |
| `"1234.5"` | JPY (0)  | `1234`  | tie; `4` is already even, so stay      |
| `"1235.5"` | JPY (0)  | `1236`  | tie; `5` is odd, so go up to `6`       |
| `"1.2345"` | KWD (3)  | `1.234` | tie; `4` is already even, so stay      |

Build the value with `Decimal(amount)` — from the **string**. Converting the
string through `float` first destroys the tie: `float("2.675")` is really
`2.67499999999999982236431605997495353221893310546875`, which is below the tie
and rounds the wrong way. Every row in the table above is a value that a
float round-trip gets wrong.

Rounding is on the magnitude, so negatives behave symmetrically and keep their
sign: `"-2.675"` in USD is `-2.68`, and `"-0.125"` in USD is `-0.12`.

## Output format

Return a plain positional decimal string with **exactly** `exponent` digits after
the point — pad with zeroes when the input had fewer (`"5"` in USD is `"5.00"`).
No thousands separators, no currency symbol or code, no exponent notation
however large the number, and no leading `+` (`"+1.5"` in USD is `"1.50"`).

When the exponent is `0` there is no fractional part, so emit **no decimal point
at all**: `"1234.5"` in JPY is `"1234"`, never `"1234."` and never `"1235.0"`.

Zero is written without a sign. An amount that is negative but rounds to zero
must normalise: `"-0.004"` in USD is `"0.00"`, not `"-0.00"`, and `"-0.4"` in
JPY is `"0"`, not `"-0"`.

## Errors

If `currency` is not a key of `exponents`, raise `KeyError`. Do this **first**,
before looking at the amount, so a call with both an unknown currency and a
malformed amount raises `KeyError` rather than `ValueError`.

If `amount` is not a string `decimal.Decimal` accepts, or parses to a non-finite
value, raise `ValueError`. `decimal` signals a bad literal with
`decimal.InvalidOperation`, which is an `ArithmeticError` and not a `ValueError`,
so that has to be translated rather than allowed to escape. Amounts such as
`""`, `"abc"`, `"1.2.3"`, `"12,34"`, `"$1.00"`, `"1 000.00"` and `"Infinity"`
are all `ValueError`.

## Out of scope

- Validating that a code in `exponents` is a real ISO 4217 code, or that its
  exponent matches the published table. The caller's table is authoritative.
- Currency conversion, symbols, locale-aware grouping, and accounting negatives
  such as `(1.00)`.
- Any caching or persistence. The function is pure.
