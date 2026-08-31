# IAM-2287 — Decide access requests against the policy set

**Component:** `platform/authz`
**Reporter:** Devansh (Platform Security)

## Background

Every service rolls its own permission check and an audit replay caught two of them
disagreeing with the console: a contractor we had cut off from `docs/reports/*` by a
DENY on the `contractor` role still read the file, because a per-user ALLOW sat
further down the list. We want one shared decision function every service calls.

## What to build

```python
def authorize(request: dict, policies: list[dict]) -> str: ...
```

It returns the string `"ALLOW"` or `"DENY"`, nothing else, and mutates neither
argument. A request has exactly the fields `subject`, `roles` (a list of role names,
possibly empty), `action` and `resource`; a policy has exactly `effect`,
`principal`, `action` and `resource`.

A policy matches only if principal, action and resource all match. `principal` is
not a pattern: it matches when it is exactly `"*"` (any principal), exactly `"user:"`
followed by the request's subject, or exactly `"role:"` followed by one of the roles
in the request's list — `"user:al*"` is the literal principal named `al*` and does
not match subject `alice`. `action` and `resource` carry one piece of syntax only, a
trailing `*`: drop it and what remains is a prefix, so `s3:Get*` matches
`s3:GetObject` and equally the bare `s3:Get`, `docs/reports/*` does not reach
`docs/reportsQ1`, and `*` alone matches everything. Any other pattern must equal the
value exactly; no glob or regex syntax is interpreted, and a non-final `*` is a
literal asterisk, so `s3:*Object` matches only the action named exactly that.
Comparison is case-sensitive throughout, `effect` included.

Combine the matching policies with deny-overrides, the XACML 3.0 Appendix C.2
rule-combining algorithm
(<https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html>): any
matching DENY gives `"DENY"`; failing that, a matching ALLOW gives `"ALLOW"`;
failing that we default-deny, so a request no policy speaks to — an empty `policies`
list included — is refused. A matching DENY decides regardless of where it sits in
the list relative to an ALLOW, regardless of how broad or narrow either policy's
action and resource patterns are, and regardless of the ALLOW naming the user
directly where the DENY only names a role, so a `role:contractor` DENY beats a
`user:alice` ALLOW for a contractor named alice; there is no most-specific-wins
tie-break and no later entry overriding an earlier one.

Validate everything before deciding anything, across every policy including ones
that would not have matched. Raise `ValueError` if the request is missing `subject`,
`roles`, `action` or `resource` or if `roles` is not a list; if any policy is
missing `effect`, `principal`, `action` or `resource`; or if any policy's `effect`
is not exactly `"ALLOW"` or exactly `"DENY"`, with the offending value verbatim in
the message — a typo like `"Allow"` or `"PERMIT"` should fail loudly rather than
read as a non-match.

## Out of scope

Conditions, time windows, IP restrictions, resource-based policies, permission
boundaries — four fields, nothing more. Role hierarchies: `roles` arrives flattened.
Reporting *which* policy decided. Caching; the function is pure.
