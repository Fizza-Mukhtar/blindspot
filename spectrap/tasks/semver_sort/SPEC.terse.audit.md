# Fairness audit — RELENG-412 (`semver_sort`), terse rendition

Question asked of every assertion in `selftest.py`: can a reader holding only
`SPEC.terse.md` plus the standard it cites normatively (Semantic Versioning
2.0.0, <https://semver.org/spec/v2.0.0.html>) derive the required answer?

The terse ticket carries the whole precedence algorithm by normative reference
to items 10 and 11 of that standard. Every clause of item 11 the assertions
exercise is quoted below by item number, so the chain from ticket to answer is
explicit.

| selftest function | determined by | verdict |
| --- | --- | --- |
| `test_spec_item_11_example_ordering` | "Order by precedence exactly as Semantic Versioning 2.0.0 defines it (<https://semver.org/spec/v2.0.0.html>, items 10 and 11), including its rules for comparing dot-separated pre-release identifiers" — item 11 of the standard prints this exact eight-tag chain as its worked example. | DETERMINED |
| `test_numeric_identifier_ranks_below_alphanumeric` | Same sentence, "including its rules for comparing dot-separated pre-release identifiers" → item 11.4.3: "Numeric identifiers always have lower precedence than non-numeric identifiers." | DETERMINED |
| `test_numeric_identifiers_compare_numerically_not_lexically` | Same sentence → item 11.4.1: identifiers consisting only of digits are compared numerically. Reinforced by the background, "The dashboard string-sorts git tags, so `v1.0.0-rc.2` lands after `v1.0.0-rc.10` … the wrong build", which states the observed order as the defect being fixed. | DETERMINED |
| `test_larger_identifier_set_wins_when_prefix_equal` | Same sentence → item 11.4.4: when all preceding identifiers are equal, the larger set of pre-release fields has higher precedence. | DETERMINED |
| `test_prerelease_ranks_below_the_normal_version` | Same sentence → item 11.3: a pre-release version has lower precedence than the associated normal version. | DETERMINED |
| `test_build_metadata_is_ignored_and_ties_are_stable` | "item 10 also puts build metadata outside precedence altogether, so `1.0.0+build.1` and `1.0.0+build.99` really do compare equal, and tags that tie must come out in the order they went in." Item 10 gives the exclusion; the stability of ties is the ticket's own local choice and is stated outright. | DETERMINED |
| `test_core_numbers_compare_numerically` | "Order by precedence exactly as Semantic Versioning 2.0.0 defines it … items 10 and 11" → item 11.2: major, minor and patch are compared numerically, in that order. | DETERMINED |
| `test_ascii_order_for_alphanumeric_identifiers` | Same sentence → item 11.4.2: identifiers with letters or hyphens are compared "lexically in ASCII sort order", which puts `A` (0x41) below `a` (0x61). | DETERMINED |
| `test_leading_v_is_accepted_and_preserved` | "Tags are `MAJOR.MINOR.PATCH` with an optional leading `v` … The `v` is decorative — it plays no part in ordering, and what you return must be the original strings, `v` and all, since the dashboard links to them by exact name." Ordering of `1.10.0` below `v2.0.0` then follows from item 11.2. | DETERMINED |
| `test_input_is_not_mutated` | "A new list of the same tag strings, lowest precedence first, without mutating the caller's list". | DETERMINED |
| `test_empty_input` | "…without mutating the caller's list; empty in, empty out." | DETERMINED |
| `test_invalid_tags_raise_value_error_naming_the_tag` (all 7 parameters: `1.0`, `1.01.0`, `1.0.0-01`, `1.0.0-`, `1.0.0-a..b`, `banana`, `""`) | "Anything not well formed per the standard's grammar raises `ValueError` with the offending tag verbatim in the message: all three core numbers present, no leading zeroes on a core number or on a purely numeric pre-release identifier, no empty identifiers." `1.0`, `banana` and `""` fail "all three core numbers present" (and the grammar of item 2); `1.01.0` and `1.0.0-01` fail the leading-zero clause (item 9 forbids leading zeroes on numeric identifiers); `1.0.0-` and `1.0.0-a..b` fail the empty-identifier clause. Sorting a list requires parsing every element, so a bad tag alongside a good one still raises. | DETERMINED |

Nothing was found underdetermined on the second pass; one clause was tightened
during the first pass (see below).

## Requirements deliberately kept in prose rather than dropped

- **Stability of equal-precedence ties.** Not settled by the standard — the
  standard only says the two versions have equal precedence. Local choice,
  stated explicitly.
- **`v` accepted, ignored for ordering, preserved in the output.** Not in the
  standard at all (`v`-prefixed tags are explicitly *not* semantic versions per
  the spec's FAQ). Local, stated explicitly.
- **`ValueError` naming the offending tag.** Local error contract, stated.
- **No mutation, new list, empty-in/empty-out.** Local, stated.
- **Grammar restatement in the error paragraph.** The first draft said only
  "not well formed per the standard's grammar". That does determine all seven
  invalid cases via items 2 and 9, but the reader would have had to reconstruct
  the BNF from a bare pointer, so the three constraints the cases turn on
  (arity, leading zeroes, empty identifiers) were written back in as a clause.

## Open questions left open

Both declared open questions in `task.yaml` remain unresolved by the terse
ticket, by construction:

1. *Whether tags differing only in the decorative leading `v` are duplicates.*
   The ticket says the `v` does not affect ordering and must be preserved on
   output. It says nothing about de-duplication, and never claims the returned
   list has the same length as the input.
2. *Whether a `ValueError` message may carry text beyond the offending tag.*
   The ticket requires the tag "verbatim in the message" — it neither forbids
   nor requires surrounding text.
