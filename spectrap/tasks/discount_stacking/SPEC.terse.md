# PRICING-2317 — Apply a stack of promotions to a cart line total

**Component:** `pricing/cart`
**Reporter:** Dani (Merchandising Platform)

## Background

Merchandising now runs promotions that stack — a 20% storewide sale, a 10%
newsletter code and a flat €5.00 loyalty credit can all land on one line — and
`cart/totals` adds the percentages together and takes one big cut at the end.
Last week a customer stacked 20% and 10% on a €100.00 line: the storefront
quoted €72.00, we quoted €70.00, support issued a goodwill credit and the margin
report was wrong for four days. We need to match the storefront, which follows
Shopify's discount-combination rules
(<https://help.shopify.com/en/manual/discounts/discount-combinations>): each
discount comes off the amount left after the previous one, so percentages
compound rather than add.

## What to build

```python
def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    ...
```

The function is pure and must not mutate `discounts` or any mapping inside it.

Money crossing this boundary is a decimal string in major units (euros, not
cents): an optional `-`, one or more digits, then optionally a `.` and one or
more digits — nothing else, so no `+`, no thousands separator, no surrounding
whitespace, no exponent, no bare `5.` or `.5`, no empty string. Inputs may carry
any number of fractional digits; the returned string always carries exactly two.
The sign of zero is not significant — return `"0.00"`, never `"-0.00"`. Use
`decimal.Decimal` throughout: the margin report reconciles against the payment
processor to the cent, so binary floating point is not acceptable anywhere in
this function.

Each element of `discounts` is a mapping with a `"kind"` and a `"value"`, e.g.
`{"kind": "percent", "value": "20"}` or `{"kind": "amount", "value": "5.00"}`.
`"value"` is a decimal string in the grammar above for both kinds — a percentage
for `percent`, so `"12.5"` is twelve and a half percent, and money in major
units for `amount`.

Quantize `subtotal` to two places and call that the running total, then walk
`discounts` in the order the caller gave them, applying each entry to the
running total the previous entry left behind — `percent` p gives
`running × (100 − p) / 100`, `amount` a gives `running − a` — and quantize back
to two places with `decimal.ROUND_HALF_EVEN` as each step finishes, since the
step after it reads that quantized figure rather than a full-precision one. The
running total never drops below zero: an amount bigger than what is left takes
it to `0.00` and the excess simply goes unused, and any discounts after that
operate on `0.00` and leave it there. An empty `discounts` list just returns the
normalised subtotal.

So `"100.00"` with 20%, then `5.00` off, then 10% runs
`100.00 → 80.00 → 75.00 → 67.50` and the answer is `"67.50"`; summing to 30%
first would give `"65.00"`, which is the bug. The order is the caller's — the
same three as `5.00` off, 20%, 10% runs `95.00 → 76.00 → 68.40`.

## Errors

Raise `ValueError`, with the offending string verbatim in the message so the
checkout logs stay searchable, when: `subtotal` is not a `str` or is malformed
by the grammar above; `subtotal` is negative (compared numerically, so `"-0.00"`
is zero and passes — a refund is a different ticket); an element of `discounts`
is not a mapping or is missing `"kind"` or `"value"`; `"kind"` is anything other
than exactly `"percent"` or `"amount"`; `"value"` is not a `str` or is malformed;
`"value"` is negative for either kind, a negative discount being a surcharge we
do not model here; or `"value"` is greater than `100` for a `percent`, though
`100` itself is fine and an `amount` has no upper bound — that is what the clamp
is for. Each entry is validated when the walk reaches it, whether or not the
running total is already `0.00` and the entry could still have changed anything.

## Out of scope

- Deciding *which* discounts may combine. Eligibility, exclusivity and the
  order-level-vs-product-level distinction are settled upstream; by the time we
  are called the list is final and correct.
- Tax, shipping, currency codes, and currencies whose minor unit is not 1/100.
- Allocating the discount back across the individual items in the line.
- Any I/O, caching or persistence. The function is pure.
