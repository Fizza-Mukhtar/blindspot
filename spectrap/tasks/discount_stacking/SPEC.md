# PRICING-2317 — Apply a stack of promotions to a cart line total

**Component:** `pricing/cart`
**Reporter:** Dani (Merchandising Platform)
**Consumers:** the cart totals endpoint, the checkout quote, the refund calculator, the nightly margin report

## Background

Merchandising has started running promotions that stack: a 20% storewide sale,
a 10% newsletter code, and a flat €5.00 loyalty credit can all land on the same
line. Our current `cart/totals` code adds the percentages together and takes one
big cut at the end, which is not what our discount engine does and not what the
customer is shown on the storefront.

Last week a customer stacked 20% and 10% on a €100.00 line. The storefront
quoted €72.00. Our totals endpoint quoted €70.00. Support issued a €2.00
goodwill credit and the margin report was wrong for four days.

The behaviour we have to match is the one described in Shopify's
discount-combination documentation
(<https://help.shopify.com/en/manual/discounts/discount-combinations>): when
discounts combine, each one is taken off **the amount that is left after the
previous one**, not off the original price. Percentages therefore compound.
They do not add.

## What to build

```python
def apply_discounts(subtotal: str, discounts: list[dict]) -> str:
    ...
```

The function is pure. It must not mutate `discounts` or any mapping inside it.

## Money representation

Every monetary quantity that crosses this boundary is a **decimal string in
major units** — euros, not cents. The accepted grammar is an optional `-`,
then one or more digits, then optionally a `.` followed by one or more digits.
Nothing else: no `+` sign, no thousands separator, no whitespace, no
exponent, no empty string. A value that is not a `str`, or is a `str` that does
not match that grammar, is malformed.

The input may carry any number of fractional digits. **The returned string
always carries exactly two.** The sign of zero is not significant: zero is
returned as `"0.00"`, never `"-0.00"`.

Use `decimal.Decimal` for the arithmetic. Binary floating point is not
acceptable anywhere in this function — the margin report reconciles against the
payment processor to the cent.

## Discount entries

Each element of `discounts` is a mapping with a `"kind"` and a `"value"`:

```python
{"kind": "percent", "value": "20"}     # take 20% off
{"kind": "amount",  "value": "5.00"}   # take 5.00 off
```

`"value"` is a decimal string in the grammar above for both kinds. For
`percent` it is a percentage, so `"20"` means twenty percent and `"12.5"` means
twelve and a half percent. For `amount` it is money in major units.

## Rules

1. **Start.** Take the `subtotal`, round it to two decimal places (see rule 3),
   and call that the *running total*.

2. **Walk the list in order.** Apply the discounts one at a time, in exactly the
   order they appear in `discounts`, each one to the current running total. The
   result of each step becomes the running total for the next step.

   - `percent` with value *p*: the new running total is
     `running_total × (100 − p) / 100`.
   - `amount` with value *a*: the new running total is `running_total − a`.

3. **Round after every step.** The running total is rounded to two decimal
   places **at the end of each step**, using the rounding mode
   `decimal.ROUND_HALF_EVEN` (banker's rounding: an exact half goes to the
   nearest even last digit, so `5.025` becomes `5.02` and `5.075` becomes
   `5.08`). This is not a cosmetic final flourish — a step operates on the
   *rounded* output of the step before it, so rounding once at the end gives a
   different answer and will not match the storefront. The rounding of the
   subtotal in rule 1 uses the same mode.

4. **Clamp at zero.** The running total never goes below zero. If subtracting a
   fixed amount would take it negative, the running total becomes `0.00`
   instead — the excess is simply not used. Any discounts that follow then
   operate on a running total of `0.00` and leave it at `0.00`.

5. **Empty stack.** If `discounts` is empty, return the subtotal, normalised to
   two decimal places by rule 3. Nothing else happens.

6. Return the final running total as a string with exactly two decimal places.

### Worked example

`apply_discounts("100.00", [{"kind": "percent", "value": "20"}, {"kind": "amount", "value": "5.00"}, {"kind": "percent", "value": "10"}])`

| step | discount   | arithmetic              | running total |
|------|------------|-------------------------|---------------|
| —    | subtotal   |                         | `100.00`      |
| 1    | 20%        | `100.00 × 80 / 100`     | `80.00`       |
| 2    | 5.00 off   | `80.00 − 5.00`          | `75.00`       |
| 3    | 10%        | `75.00 × 90 / 100`      | `67.50`       |

The answer is `"67.50"`. Adding the percentages first (30% off, then €5) would
give `"65.00"`, which is the bug we are fixing.

Order matters, and the order is the caller's. The same three-way stack applied
as *5.00 off, then 20%, then 10%* gives `95.00 → 76.00 → 68.40`.

## Errors

Raise `ValueError` for each of the following. The message must contain the
offending string verbatim so the checkout logs are searchable.

- `subtotal` is malformed by the grammar above, or is not a `str`.
- `subtotal` is negative. (A cart line total cannot be negative; a refund is a
  different ticket.)
- An element of `discounts` is not a mapping, or is missing `"kind"` or
  `"value"`.
- `"kind"` is anything other than `"percent"` or `"amount"`.
- `"value"` is malformed by the grammar above, or is not a `str`.
- `"value"` is negative, for either kind. A negative discount is a surcharge and
  we do not model surcharges here.
- `"value"` is greater than `100` for a `percent` discount. There is no upper
  bound on an `amount` discount — that is what rule 4 is for.

Validation is unconditional: a discount is checked when the walk reaches it,
and an invalid discount raises **even if the running total has already been
clamped to `0.00`** and the discount would have had no effect.

## Out of scope

- Deciding *which* discounts are allowed to combine. Eligibility, exclusivity
  and the order-level-vs-product-level distinction are settled upstream; by the
  time we are called, the list is final and correct.
- Tax, shipping, currency codes, and currencies with a minor unit that is not
  1/100. Every amount here is two-decimal major units.
- Allocating the discount back across the individual items in the line.
- Any I/O, caching or persistence. The function is pure.
