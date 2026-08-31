# PLAT-2291 — Render byte counts with the correct SI or IEC prefix

**Component:** `platform/humanize`
**Reporter:** Marcus (Storage Platform)
**Consumers:** the quota emails, the bucket browser, the ingest CLI's `--progress` line

## Background

Storage support has escalated three tickets this quarter from customers who
believe we are overcharging them. In every case the customer compared the
"1.0 GB used" line in our quota email against their own `du` output and found a
7% gap. The cause is us: the quota email divides by 1024 and then labels the
result `GB`, so a mebibyte-shaped number is wearing a gigabyte-shaped hat.

Billing meters storage in **powers of ten** — that is what the contract says and
what the invoice line item means. The bucket browser, on the other hand, shows
on-disk block usage and genuinely wants **powers of two**. Both surfaces should
go through one formatter that is honest about which system it is using, so the
label always matches the arithmetic.

The two systems and their symbols are the ones defined by the BIPM for SI
decimal prefixes (<https://www.bipm.org/en/measurement-units/si-prefixes>) and by
IEC 80000-13 for the binary prefixes
(<https://www.iec.ch/prefixes-binary-multiples>).

## What to build

```python
def format_bytes(n: int, binary: bool = False) -> str:
    ...
```

`n` is a count of bytes. `binary` selects the prefix system. It defaults to
`False`, i.e. SI, because the billing surfaces are the majority caller.

## The two unit ladders

When `binary` is `False`, the divisor is **1000** and the units are, in order:

```
B    kB    MB    GB    TB    PB
```

Note the kilo symbol: SI spells it with a **lowercase `k`**, so one thousand
bytes is `1.0 kB`. The uppercase `K` belongs to the other ladder, and only
there. Every other SI symbol here is uppercase.

When `binary` is `True`, the divisor is **1024** and the units are, in order:

```
B    KiB    MiB    GiB    TiB    PiB
```

IEC 80000-13 capitalises the kibi symbol, so 1024 bytes is `1.0 KiB`. Each of
these is exactly `1024**k` bytes: `1 MiB` is 1 048 576 bytes, not 1 000 000.

The two ladders never mix. `kB` is always 1000 bytes and `KiB` is always 1024
bytes, whichever mode is selected.

## How the number is rendered

Take the sign off first: if `n` is negative, the output is a leading `-`
followed by exactly what the magnitude `abs(n)` would produce on its own.
`n = 0` produces `0 B`.

Pick the unit: the largest unit on the selected ladder whose divisor is less
than or equal to the magnitude, capped at `PB` / `PiB` (see below).

- If the chosen unit is **`B`** — that is, the magnitude is below the divisor —
  print the magnitude as a plain integer with **no decimal point at all**:
  `999 B`, `1000 B` in binary mode, `0 B`.
- For **every unit above `B`**, print the magnitude divided by that unit's
  divisor with **exactly one digit after the decimal point**, always: `1.0 kB`,
  not `1 kB` and not `1.00 kB`.

Rounding to that one decimal digit is **round half up on the magnitude**: a
displayed value of exactly `x.x5` rounds away from zero, so 1150 bytes is
`1.2 kB`, not `1.1 kB`. (Do not let binary floating point decide this for you;
`round()` will not give you half-up.)

There is exactly **one space** between the number and the unit symbol, and no
other whitespace. No thousands separators anywhere in the number.

## Promotion after rounding

This is the part the old quota-email code got wrong even before the ladder
question. Rounding happens *before* the label is attached, so rounding can push
the displayed number up to the next unit boundary, and when it does the value
must be **promoted to the next unit** and the division redone there.

999 950 bytes in SI mode is 999.95 kB, which rounds half up to 1000.0 kB. A
displayed `1000.0 kB` is not acceptable output: 1000.0 kB *is* 1 MB. Re-divide
in the larger unit and print `1.0 MB`. Concretely, if the rounded display value
would be `1000.0` or greater in SI (`1024.0` or greater in IEC) and a larger
unit is available, move up one unit and round again there.

One byte less does **not** promote: 999 949 bytes is `999.9 kB`.

The same applies in binary mode: 1 048 575 bytes is 1023.999… KiB, which rounds
to 1024.0 KiB and must therefore be printed as `1.0 MiB`.

## Above the top of the ladder

`PB` and `PiB` are the largest units we emit. A magnitude that would need a
bigger prefix simply keeps growing inside the top unit — the integer part is not
capped and the promotion rule has nowhere to promote to. So
1 500 000 000 000 000 000 bytes in SI mode is `1500.0 PB`, and `2**60` bytes in
binary mode is `1024.0 PiB`.

## Worked examples

| `n` | `binary=False` | `binary=True` |
| --- | --- | --- |
| `0` | `0 B` | `0 B` |
| `999` | `999 B` | `999 B` |
| `1000` | `1.0 kB` | `1000 B` |
| `1024` | `1.0 kB` | `1.0 KiB` |
| `1150` | `1.2 kB` | `1.1 KiB` |
| `999_949` | `999.9 kB` | `976.5 KiB` |
| `999_950` | `1.0 MB` | `976.5 KiB` |
| `1_048_575` | `1.0 MB` | `1.0 MiB` |
| `-1500` | `-1.5 kB` | `-1.5 KiB` |

## Errors

`n` must be an `int`. Anything else — a `float` (including a whole-valued one
like `1000.0`), a `str`, `None`, a `Decimal` — raises `TypeError`. Python treats
`bool` as a subtype of `int`, but `True` is not a byte count: `format_bytes(True)`
must raise `TypeError` as well.

There is no upper or lower bound on a valid `int` input; arbitrarily large
values are fine.

## Out of scope

- Bit units (`kbit`, `Kibit`) and transfer rates.
- Localisation: the decimal separator is always `.`, in every locale.
- Parsing a formatted string back into a byte count. That is PLAT-2304.
