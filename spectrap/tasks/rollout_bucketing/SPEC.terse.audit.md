# SPEC.terse.md determinacy audit — FLAG-238 (`rollout_bucketing`)

Every test function in `selftest.py`, checked against `SPEC.terse.md` alone
(plus the normatively cited pages). Verdict is DETERMINED only if a reader with
just the terse ticket can derive the asserted answer.

| selftest function | determined by | verdict |
| --- | --- | --- |
| `test_worked_example_from_the_spec` | "Join the two identifiers with a single ASCII colon, encode UTF-8, take the SHA-256 digest, read it as one unsigned big-endian integer and reduce modulo 100; the user is enabled when the bucket is strictly less than `percentage`" — plus the ticket's own check: "`\"checkout-v2:user-1042\"` is bucket 19: off at 19, on at 20." | DETERMINED |
| `test_worked_example_same_user_other_flag` | Same pinned formula (and the literal one-line transcription in the code block), which yields bucket 10 for `search-rerank:user-1042`; "enabled when the bucket is strictly less than `percentage`" fixes off at 10 / on at 11. | DETERMINED |
| `test_exact_pinned_bucket_values` | The code block `bucket = int(hashlib.sha256(f"{flag_key}:{user_id}".encode("utf-8")).hexdigest(), 16) % 100`, plus "strictly less than `percentage`" for each `(bucket, bucket+1)` boundary pair. | DETERMINED |
| `test_agrees_with_the_pinned_formula_across_a_grid` | Same code block; "encode UTF-8, take the SHA-256 digest" fixes the digest and the encoding for every flag/user in the grid, including the empty and non-ASCII entries. | DETERMINED |
| `test_percentage_zero_disables_everyone` | "At the ends, `0` disables everyone (nothing is `< 0`)". | DETERMINED |
| `test_percentage_hundred_enables_everyone` | "`100` enables everyone (every bucket `0`–`99` is `< 100`), so nobody stays dark at full rollout." | DETERMINED |
| `test_monotonic_over_the_whole_ramp` | "not the percentage, since a user in the rollout at one percentage has to still be in at every higher one" — the ramp is therefore a single off→on flip. Reinforced by the Unleash reference on widening one fixed ordering. | DETERMINED |
| `test_enabled_cohort_only_grows_as_the_flag_ramps` | "a ramp may only add users, never drop one". | DETERMINED |
| `test_assignment_does_not_depend_on_the_percentage` | "The material is the two identifiers and the colon between them and nothing else, no salt, no namespace and not the percentage" — the bucket is a pure function of the pair, so the ramp is exactly `bucket < p`. | DETERMINED |
| `test_material_is_the_two_ids_joined_by_a_single_colon` | "Join the two identifiers with a single ASCII colon" makes `("a:b","c")` and `("a","b:c")` both produce `"a:b:c"`; "Nothing else is rejected" confirms neither call raises. The `6`/`7` boundary follows from the pinned formula. | DETERMINED |
| `test_non_ascii_identifiers_are_encoded_as_utf8` | "encode UTF-8" in the rule, and "non-ASCII identifiers are covered by the UTF-8 step" in Errors. Bucket 54 for `billing-retry:üser-é☃` follows from the code block. | DETERMINED |
| `test_empty_identifiers_are_permitted_and_hash_normally` | "Nothing else is rejected: empty identifiers are legitimate (the analytics job evaluates anonymous sessions, whose user id is empty) and hash like any other string" — the bucket values then follow from the code block. | DETERMINED |
| `test_returns_an_actual_bool` | "Returns an actual `bool`." | DETERMINED |
| `test_result_is_stable_across_repeated_calls` | "Pure: same arguments, same answer, in any process, on any machine, in any Python build." | DETERMINED |
| `test_out_of_range_percentage_raises_value_error` | "An `int` percentage outside the inclusive `0`–`100` range raises `ValueError`." | DETERMINED |
| `test_non_int_percentage_raises_type_error` | "a `percentage` that is not an `int` — floats included, even integral ones like `50.0`, and `bool` included, since `True`/`False` satisfy `isinstance(x, int)` but are not percentages" (covers `50.0`, `0.0`, `100.0`, `"50"`, `None`, `True`, `False`, `(50,)`). | DETERMINED |
| `test_non_str_identifiers_raise_type_error` | "A non-`str` `flag_key` or `user_id` raises `TypeError`" (covers `None`, `42`, `b"user-42"`, `["user-42"]`, `3.5` in either position). | DETERMINED |
| `test_type_check_precedes_range_check` | "Types before range." and "Types first means `is_enabled(\"f\", \"u\", 101.0)` is a `TypeError`, not a `ValueError`." — `-1.0` follows from the same ordering. | DETERMINED |

18 test functions audited, 18 DETERMINED, 0 UNDERDETERMINED.

## Deliberately left open (unchanged from the detailed rendition)

- Whether a `flag_key` containing `:` should be *rejected*, given that
  `("a:b", "c")` and `("a", "b:c")` collide onto the same material. The terse
  ticket fixes the behaviour (they are accepted and they collide) but, like the
  detailed rendition, never says whether that is the right design.
- Whether the residual modulo bias is acceptable — `2**256` is not divisible by
  100, so the buckets are not exactly equiprobable. The formula is pinned; the
  ticket takes no position on the bias.
