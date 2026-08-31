# SPEC.terse.md determination audit — LEDGER-238 (`allocate_money`)

Every assertion in `selftest.py`, checked against `SPEC.terse.md` alone (plus the
normatively cited Money-pattern / largest-remainder procedure).

| selftest function | determined by | verdict |
|---|---|---|
| `test_conservation_the_parts_sum_to_the_whole` (13 cases) | "`sum(allocate(total_cents, weights)) == total_cents` must hold for every input the function accepts; where that identity and your arithmetic disagree, the identity wins." | DETERMINED |
| `test_result_is_one_amount_per_payee` (13 cases) | "Return a new list of integers, same length as `weights` and in the same order, without mutating the input." | DETERMINED |
| `test_fowler_five_cents_split_two_ways` (`[3, 2]`) | Floors from "Each payee provisionally takes the floor of that claim and carries a fractional remainder of `(total_cents * weights[i]) % W` over `W`" give `[2, 2]` with equal remainders; the single leftover unit is placed by "where two payees carry exactly the same remainder the earlier index takes the unit". | DETERMINED |
| `test_worked_example_from_the_ticket` | "So `allocate(10, [1, 2, 4])` is `[1, 3, 6]`: floors `[1, 2, 5]`, remainders 3/7, 6/7 and 5/7, two units to place, payees 1 and 2 take one each and payee 0 gains nothing." | DETERMINED |
| `test_leftover_goes_to_the_largest_remainders_not_the_first_payees` | Same worked-example sentence, plus "handed out one each to the payees holding the largest remainders, biggest remainder first". | DETERMINED |
| `test_hamilton_apportionment_example` (`100, [404, 397, 199]`) | "The floors fall short of the total by `leftover = total_cents - sum(floors)` units, handed out one each to the payees holding the largest remainders, biggest remainder first" — floors 40/39/19, remainders .4/.7/.9, two units to indices 2 then 1. | DETERMINED |
| `test_tie_on_remainder_is_broken_by_lowest_index` (`[34,33,33]`, `[2,1,1,1]`) | "where two payees carry exactly the same remainder the earlier index takes the unit". | DETERMINED |
| `test_no_payee_receives_more_than_one_extra_unit` | "No payee gains more than one extra unit", with the floor defined by "Each payee provisionally takes the floor of that claim". | DETERMINED |
| `test_zero_weight_receives_exactly_zero` (`[0,6,5]`, `[0,9,0]`) | "A weight of `0` gives an exact claim and remainder of `0`, so that payee receives exactly `0`." The 6/5 split of the remaining unit in `[0,1,1]` comes from the same-remainder / earlier-index clause. | DETERMINED |
| `test_exact_division_leaves_no_remainder_to_distribute` | "The floors fall short of the total by `leftover = total_cents - sum(floors)` units" — when the floors already sum to the total the leftover is 0 and nothing is handed out. | DETERMINED |
| `test_zero_total_pays_nobody` | "`allocate(0, weights)` is all zeros." | DETERMINED |
| `test_single_payee_takes_the_whole_amount` (`[7]`, `[-7]`) | Conservation identity above with one term, plus "allocate `abs(total_cents)` by the rules above and negate every element". | DETERMINED |
| `test_negation_symmetry_for_negative_totals` (13 cases, both signs) | "The sign is factored out before anything else: allocate `abs(total_cents)` by the rules above and negate every element, so `allocate(-t, weights) == [-x for x in allocate(t, weights)]`" — stated via `abs`, so it holds for a negative `total` argument too. | DETERMINED |
| `test_negative_total_distributes_the_leftover_by_magnitude` (`[-3,-2]`, `[-1,-3,-6]`) | "the leftover follows magnitude rather than numeric value. That makes `allocate(-5, [1, 1])` equal `[-3, -2]`, not the `[-2, -3]` floored division on the signed total gives." `[-1,-3,-6]` follows by negating the `[1, 3, 6]` worked example. | DETERMINED |
| `test_input_list_is_not_mutated` | "...same order, without mutating the input." | DETERMINED |
| `test_empty_weights_raises_value_error` | "Raise `ValueError`, with a message saying which rule was broken, when `weights` is empty..." | DETERMINED |
| `test_negative_weight_raises_value_error` | "...when any weight is negative..." | DETERMINED |
| `test_all_zero_weights_raises_value_error` | "...or when every weight is zero, leaving no basis to divide on." | DETERMINED |
| `test_validation_runs_whatever_the_total_is` (0, 5, -5) | "Validation happens before any allocation and applies whatever `total_cents` is, including `0`." | DETERMINED |

**Result:** 19 test functions (45 parametrised assertions counted individually);
all DETERMINED, none required a requirement to be restored after the first draft.

**Deliberately left open** (as in the detailed rendition, and not asserted by any
test): which rule the `ValueError` message names when several are broken at once,
and whether `bool` values in `weights` are acceptable as `0`/`1`.
