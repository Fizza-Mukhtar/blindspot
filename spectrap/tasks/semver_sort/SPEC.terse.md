# RELENG-412 — Order release tags by Semantic Versioning precedence

**Component:** `releng/tagsort`
**Reporter:** Priya (Release Engineering)

## Background

The dashboard string-sorts git tags, so `v1.0.0-rc.2` lands after
`v1.0.0-rc.10` and the rollback picker offers the wrong build. The changelog
generator and the "latest stable" resolver read the same order.

## What to build

```python
def sort_versions(tags: list[str]) -> list[str]:
    ...
```

A new list of the same tag strings, lowest precedence first, without mutating
the caller's list; empty in, empty out. Tags are `MAJOR.MINOR.PATCH` with an
optional leading `v`, an optional pre-release part after `-` and optional build
metadata after `+` (`v1.0.0-rc.1+build.72`, `0.9.12+exp.sha.5114f85`). The `v`
is decorative — it plays no part in ordering, and what you return must be the
original strings, `v` and all, since the dashboard links to them by exact name.

Order by precedence exactly as Semantic Versioning 2.0.0 defines it
(<https://semver.org/spec/v2.0.0.html>, items 10 and 11), including its rules
for comparing dot-separated pre-release identifiers; item 10 also puts build
metadata outside precedence altogether, so `1.0.0+build.1` and `1.0.0+build.99`
really do compare equal, and tags that tie must come out in the order they went
in.

Anything not well formed per the standard's grammar raises `ValueError` with
the offending tag verbatim in the message: all three core numbers present, no
leading zeroes on a core number or on a purely numeric pre-release identifier,
no empty identifiers.

## Out of scope

- Comparing tags across repositories.
- Caching or persistence; the function is pure.
