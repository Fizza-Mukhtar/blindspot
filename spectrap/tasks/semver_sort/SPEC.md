# RELENG-412 — Order release tags by Semantic Versioning precedence

**Component:** `releng/tagsort`
**Reporter:** Priya (Release Engineering)
**Consumers:** the changelog generator, the "latest stable" resolver, the rollback picker

## Background

Our release dashboard currently sorts git tags with a plain string sort, so
`v1.0.0-rc.2` lands after `v1.0.0-rc.10` and the rollback picker offers the
wrong build. We need a proper Semantic Versioning 2.0.0 comparison.

## What to build

```python
def sort_versions(tags: list[str]) -> list[str]:
    ...
```

Return a **new** list holding the same tag strings, ordered from lowest
precedence to highest. Do not mutate the input.

## Accepted input format

Each tag is `MAJOR.MINOR.PATCH` with an optional leading `v`, an optional
pre-release part introduced by `-`, and optional build metadata introduced
by `+`. Examples of tags we actually have in the repo:

```
v2.1.0
1.0.0-alpha
1.0.0-alpha.1
v1.0.0-rc.1+build.72
0.9.12+exp.sha.5114f85
```

The leading `v` is decorative. It does not affect ordering, and the returned
strings must be the original strings, `v` and all — the dashboard links to
them by exact name.

## Ordering rules

Precedence is determined exactly as Semantic Versioning 2.0.0 defines it
(<https://semver.org/spec/v2.0.0.html>, items 10 and 11):

1. Compare `MAJOR`, then `MINOR`, then `PATCH` **numerically**. `1.0.10` is
   above `1.0.9`.
2. When the numeric parts are equal, a version **with** a pre-release part has
   **lower** precedence than the same version without one. `1.0.0-rc.1` sits
   below `1.0.0`.
3. When both have a pre-release part, compare the dot-separated identifiers
   left to right until a difference is found:
   - identifiers made up only of digits are compared **numerically**, so
     `rc.2` sits below `rc.10`;
   - identifiers containing a letter or a hyphen are compared **lexically in
     ASCII sort order**;
   - a purely numeric identifier always has **lower** precedence than an
     identifier that is not purely numeric;
   - if every identifier compared so far is equal, the version with **more**
     identifiers has the **higher** precedence.
4. **Build metadata is ignored entirely when determining precedence.**
   `1.0.0+build.1` and `1.0.0+build.99` have equal precedence.

Because of rule 4, two different tags can compare equal. When that happens the
sort must be **stable**: tags of equal precedence keep the relative order they
had in the input.

For reference, this is the ordering the spec's own example produces:

```
1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta
            < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0
```

## Errors

If a tag does not match the accepted format, raise
`ValueError` whose message contains the offending tag verbatim. Numeric parts
must not carry leading zeroes (`1.01.0` is invalid); a pre-release identifier
that is purely numeric must not carry leading zeroes either (`1.0.0-rc.01` is
invalid). Empty identifiers (`1.0.0-`, `1.0.0-a..b`) are invalid.

An empty input list returns an empty list.

## Out of scope

- Comparing tags across repositories.
- Any caching or persistence. The function is pure.
