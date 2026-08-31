# SPEC.terse.md determination audit — RATE-338 (`token_bucket`)

19 test functions in `selftest.py` (29 assertion cases once the two
`parametrize` blocks are expanded). Every one is DETERMINED by a sentence of
`SPEC.terse.md` or by the clause of RFC 2697 section 2 that it normatively
cites.

| selftest function | determined by | verdict |
|---|---|---|
| `test_bucket_starts_full` | "bucket initially full" (RFC 2697 s2: `Tc(0) = CBS`), restated operationally as "carry a token count starting at `capacity` and a mark for the timestamp that count was last brought up to date, starting at the first entry's timestamp" | DETERMINED |
| `test_worked_example_from_the_ticket` | The full per-entry procedure: "Per entry, first accrue — `tokens = min(capacity, tokens + (timestamp - mark) * refill_per_second)` — and move the mark to `timestamp`, which happens for every entry in the trace regardless of whether the request is admitted or rejected. Then admit when `tokens + 1e-9 >= cost` … on admission set `tokens = max(0.0, tokens - cost)`. A rejection consumes nothing and leaves the count as the accrual step left it" — walks to `[True, False, False, True]` | DETERMINED |
| `test_accrual_mark_advances_across_a_rejection` | "move the mark to `timestamp`, which happens for every entry in the trace regardless of whether the request is admitted or rejected" — entry 2 accrues from t=5, not t=0 | DETERMINED |
| `test_continuous_accrual_at_sub_second_polls` | "we accrue continuously, so between trace entries `elapsed` seconds apart the bucket gains exactly `elapsed * refill_per_second` tokens as a real number, with no flooring, rounding, truncation or bucketing into whole tokens or whole seconds", plus the inclusive `tokens + 1e-9 >= cost` | DETERMINED |
| `test_fractional_accrual_over_a_fractional_rate` | Same continuous-accrual sentence plus its example "A 40 ms gap at 5 tokens/second is worth 0.2 tokens, and five such gaps a whole token", and "a burst recorded at the same instant accrues nothing between its members" for the repeated `0.08` | DETERMINED |
| `test_token_count_is_clamped_at_capacity` | "count never incremented past the bucket size" (RFC 2697 s2 increments `Tc` only if `Tc < CBS`), made explicit in `tokens = min(capacity, …)` | DETERMINED |
| `test_cost_exceeding_capacity_is_never_admitted_and_consumes_nothing` | "A rejection consumes nothing and leaves the count as the accrual step left it, which with the cap at `capacity` means a cost above `capacity + 1e-9` is never admitted however long the customer waits, and the entry behind it still sees the bucket it would otherwise have seen" | DETERMINED |
| `test_rejection_leaves_the_token_count_untouched` | "a rejected request leaving the count untouched" / "A rejection consumes nothing and leaves the count as the accrual step left it" (RFC 2697 s2: a non-green packet leaves `Tc` unchanged) | DETERMINED |
| `test_cost_equal_to_the_credit_on_hand_is_admitted` | "admit when `tokens + 1e-9 >= cost` … so a cost equal to the credit on hand is admitted" (RFC 2697 s2: green when `Tc - B >= 0`) | DETERMINED |
| `test_cost_above_the_credit_on_hand_is_rejected` | Same comparison, taken negatively: at t=1 the count is 1.0 and `1.0 + 1e-9 >= 1.5` is false | DETERMINED |
| `test_admission_tolerance_is_one_nanotoken` | "admit when `tokens + 1e-9 >= cost`, an absolute slack against floating-point drift" — 5e-10 falls inside it, 1e-6 does not | DETERMINED |
| `test_burst_at_a_shared_timestamp_accrues_nothing` | "Timestamps are non-decreasing, and entries may share one: a burst recorded at the same instant accrues nothing between its members, so its second entry sees whatever the first left behind" | DETERMINED |
| `test_zero_cost_is_admitted_against_an_empty_bucket` | "A cost of exactly zero is legal and is always admitted, even against an empty bucket" | DETERMINED |
| `test_empty_trace_returns_empty_list` | "an empty trace returns an empty list" | DETERMINED |
| `test_decreasing_timestamp_raises` | "`ValueError` … if a timestamp is strictly less than the one before it — that last means the trace is corrupt" | DETERMINED |
| `test_non_positive_or_non_finite_parameters_raise` (7 cases) | "`ValueError` if `capacity` or `refill_per_second` is not a finite number greater than zero" — covers `0.0`, `-1.0`, `inf`, `nan` for capacity and `0.0`, `-2.5`, `inf` for the rate | DETERMINED |
| `test_negative_or_non_finite_cost_raises` (5 cases) | "if a cost is negative or is not a finite number" — covers `-1e-9`, `-0.5`, `-3.0`, `nan`, `inf` | DETERMINED |
| `test_non_finite_timestamp_raises` | "if a timestamp is not a finite number" | DETERMINED |
| `test_input_trace_is_not_mutated` | "Do not mutate the input" | DETERMINED |

## Open questions deliberately left open

Neither declared open question is resolved by the terse ticket:

- Timestamps are constrained only to be finite and non-decreasing; nothing says
  they must be non-negative or sit on any particular epoch.
- The ticket names `ValueError` but says nothing about the message wording, so
  whether it must identify the offending entry remains unsettled.
