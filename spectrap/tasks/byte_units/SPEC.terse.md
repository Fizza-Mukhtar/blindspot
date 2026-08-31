# PLAT-2291 — Render byte counts with the correct SI or IEC prefix

**Component:** `platform/humanize`
**Reporter:** Marcus (Storage Platform)
**Consumers:** the quota emails, the bucket browser, the ingest CLI's `--progress` line

## Background

Three "you are overcharging us" escalations this quarter, all the same bug: the
quota email divides by 1024 and then labels the result `GB`, so the customer
compares it against their own `du` and finds a 7% gap. Billing meters storage in
powers of ten because that is what the contract says and what the invoice line
item means; the bucket browser shows on-disk block usage and genuinely wants
powers of two. Both surfaces should go through one formatter that is honest
about which system it is using.

## What to build

```python
def format_bytes(n: int, binary: bool = False) -> str:
    ...
```

`n` is a count of bytes. `binary` selects the prefix system and defaults to
`False`, i.e. SI, because the billing surfaces are the majority caller.

## Rendering

Use the two prefix systems exactly as published — BIPM for the SI decimal
prefixes (<https://www.bipm.org/en/measurement-units/si-prefixes>), IEC 80000-13
for the binary ones (<https://www.iec.ch/prefixes-binary-multiples>) — including
their capitalisation, which is precisely where this has bitten us before: SI
runs `B kB MB GB TB PB` over a divisor of 1000 with kilo spelled lowercase, IEC
runs `B KiB MiB GiB TiB PiB` over a divisor of 1024 with kibi capitalised, and
the two ladders never mix, so 1024 bytes is `1.0 kB` in SI but `1.0 KiB` in IEC,
while 1000 bytes is `1.0 kB` in SI and still `1000 B` in IEC.

Take the sign off first: a negative `n` prints `-` followed by exactly what the
magnitude `abs(n)` would produce on its own, and `0` is `0 B`. Pick the largest
unit on the selected ladder whose divisor is at most the magnitude. In `B` print
the magnitude as a plain integer with no decimal point at all; in every unit
above `B` print the magnitude divided by that unit's divisor with exactly one
digit after the decimal point, always — `1.0 kB`, never `1 kB` and never
`1.00 kB`. That digit is rounded half up on the magnitude, away from zero at
exactly `x.x5`, so 1150 bytes is `1.2 kB` and 1050 bytes is `1.1 kB`; neither
`round()` nor an f-string `:.1f` will give you that, both being half-to-even
over binary floats. Exactly one space sits between the number and the symbol,
there is no other whitespace, the decimal separator is `.` and there are no
thousands separators anywhere.

Because the digit is rounded before the label is attached, rounding can carry
the displayed value up onto the next boundary, and when it does the value is
promoted to the next unit and divided again there: 999 950 bytes is 999.95 kB,
which rounds half up to 1000.0 kB, and 1000.0 kB *is* 1 MB, so the output is
`1.0 MB` — whereas one byte less, 999 949, is `999.9 kB` and does not move.
Binary behaves identically: 1 048 575 bytes is 1023.999… KiB, rounds to 1024.0
KiB, and therefore prints `1.0 MiB`. `PB` and `PiB` are the top of their
ladders and promotion has nowhere to go, so above them the integer part simply
keeps growing: 1 500 000 000 000 000 000 bytes in SI is `1500.0 PB`, and `2**60`
bytes in binary is `1024.0 PiB`.

## Errors

`n` must be an `int`. A `float` — including a whole-valued one like `1000.0` —
a `str`, `None`, a `Decimal`, or anything else raises `TypeError`. Python treats
`bool` as a subtype of `int`, but `True` is not a byte count, so
`format_bytes(True)` raises `TypeError` as well. There is no upper or lower
bound on a valid `int`; arbitrarily large magnitudes are fine.

## Out of scope

- Bit units (`kbit`, `Kibit`) and transfer rates.
- Localisation: the decimal separator is always `.`, in every locale.
- Parsing a formatted string back into a byte count. That is PLAT-2304.
