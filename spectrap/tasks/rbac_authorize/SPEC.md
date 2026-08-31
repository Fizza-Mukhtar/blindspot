# IAM-2287 — Decide access requests against the policy set

**Component:** `platform/authz`
**Reporter:** Devansh (Platform Security)
**Consumers:** the document service, the object-store gateway, the audit replay tool

## Background

Every service in the platform currently rolls its own permission check, and the
audit replay we ran last quarter showed two of them disagree with the console.
The worst case: a contractor was removed from `docs/reports/*` by a DENY on the
`contractor` role, but the document service still let them read the file because
a per-user ALLOW happened to sit later in the list and won. Legal was not happy.

We want one shared decision function that every service calls, and it must
behave exactly like the deny-overrides rule that our console, our audit tool and
our cloud provider already use.

## What to build

```python
def authorize(request: dict, policies: list[dict]) -> str:
    ...
```

It returns the string `"ALLOW"` or the string `"DENY"`. Nothing else. It does
not mutate either argument.

A **request** is a dict with exactly these fields:

```python
{"subject": "alice", "roles": ["dev", "oncall"],
 "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
```

`roles` is a list of role names; it may be empty. A **policy** is a dict with
exactly these fields:

```python
{"effect": "ALLOW", "principal": "role:dev",
 "action": "s3:Get*", "resource": "docs/reports/*"}
```

## When a policy matches the request

A policy matches only if all three of its fields match.

**Principal.** The `principal` field is not a pattern. It matches when it is
exactly the string `"*"` (meaning any principal), or exactly `"user:"` followed
by the request's `subject`, or exactly `"role:"` followed by one of the roles in
the request's `roles` list. `"user:al*"` does not match subject `alice`; it is
the literal principal named `al*`.

**Action and resource.** These two fields are patterns with exactly one piece of
syntax: a trailing `*`. If the pattern's **last character** is `*`, drop that
character and the pattern matches any value that **starts with** what remains —
so `s3:Get*` matches `s3:GetObject`, `s3:GetBucket` and also the bare `s3:Get`
itself, while `docs/reports/*` does not match `docs/reportsQ1` (there is no
slash). The pattern `*` on its own therefore matches everything. If the last
character is not `*`, the pattern must equal the value exactly.

There is no other glob syntax. `?`, `[...]`, `**` and regular expressions are
not interpreted. In particular a `*` anywhere other than the final character is
a **literal asterisk**: the pattern `s3:*Object` does not match `s3:GetObject`,
it matches only the action literally named `s3:*Object`.

All matching — principals, actions, resources, and the `effect` values below —
is **case-sensitive**. `S3:GetObject` and `s3:GetObject` are different actions.

## Combining the matching policies

Use the deny-overrides combining algorithm from XACML 3.0, §C.2 of
<https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html> — the
same rule AWS IAM applies to identity policies:

1. If **any** matching policy has effect `DENY`, the result is `"DENY"`.
2. Otherwise, if **at least one** matching policy has effect `ALLOW`, the result
   is `"ALLOW"`.
3. Otherwise the result is `"DENY"`. This is the default-deny fallback: a
   request that no policy speaks to is refused. An empty `policies` list is the
   degenerate case of this and returns `"DENY"`.

Rule 1 is unconditional and this is the part the current services get wrong.
A matching DENY wins over a matching ALLOW **regardless of the order** the two
policies appear in the list, **regardless of how specific** their action or
resource patterns are (a `DENY` on `*`/`*` beats an `ALLOW` on the exact action
and the exact resource), and **regardless of how specific the principal is** — a
`role:contractor` DENY beats a `user:alice` ALLOW for a contractor named alice.
There is no "most specific wins" tie-break anywhere in this function, and there
is no notion of a policy later in the list overriding an earlier one.

### Worked example

```python
request = {"subject": "alice", "roles": ["contractor"],
           "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
policies = [
    {"effect": "DENY",  "principal": "role:contractor",
     "action": "*",        "resource": "docs/reports/*"},
    {"effect": "ALLOW", "principal": "user:alice",
     "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
]
authorize(request, policies)   # -> "DENY"
```

Both policies match. The ALLOW is later, narrower, and names the user directly;
none of that matters. Reversing the two list entries gives `"DENY"` as well.

## Errors

Validate everything **before** deciding anything, so that a malformed policy is
reported even when an earlier policy would already have settled the outcome:

- If `request` is missing any of `subject`, `roles`, `action` or `resource`, or
  if `roles` is not a list, raise `ValueError`.
- If any policy is missing any of `effect`, `principal`, `action` or `resource`,
  raise `ValueError`.
- If any policy's `effect` is not exactly `"ALLOW"` or exactly `"DENY"`, raise
  `ValueError` whose message contains the offending effect value verbatim.
  `"Allow"`, `"allow"`, `"deny"` and `"PERMIT"` are all invalid — we would rather
  fail loudly than silently treat a typo as a non-match.

This validation covers every policy in the list, including policies that would
not have matched the request.

## Out of scope

- Conditions, time windows, IP restrictions, resource-based policies, permission
  boundaries and any other IAM feature. Four fields, nothing more.
- Role hierarchies or role inheritance. The `roles` list is already flattened by
  the caller.
- Explaining *which* policy produced the decision. Callers only get the verdict;
  the audit tool re-runs the policies itself when it needs a reason.
- Caching. The function is pure and is called on every request.
