"""Deterministic input generator for differential fuzzing.

The forge calls ``sample(rng)`` many times, runs the candidate and the reference
on each input, and keeps the first input where they disagree.  The generator is
domain-aware on purpose: uniformly random strings would essentially never make
two policies match the *same* request, and it is exactly the overlap of a
matching ALLOW with a matching DENY that the deny-overrides rule is about.

So most policy fields are *derived from the request that was just drawn*: a
principal that really names the subject or one of its roles, and an action or
resource pattern that really covers the requested one, at a randomly chosen
specificity (bare ``*``, a random-length trailing-``*`` prefix, or the exact
string).  That makes several policies match the same request routinely, so an
ALLOW and a DENY collide often and their list order, their specificity and their
principal specificity all vary freely across samples.  The remaining fields come
from the small near-miss pools below -- case-shifted patterns, an interior
(literal) asterisk, a principal that looks like a prefix pattern but is not --
so non-matching policies stay in the mix.  A small slice of samples carries a
malformed effect or a missing field so the validation path is exercised too.
"""

from __future__ import annotations

import random

SUBJECTS = ["alice", "bob", "carol"]

ROLE_SETS = [
    [],
    ["dev"],
    ["dev", "oncall"],
    ["contractor"],
    ["contractor", "dev"],
    ["admin"],
]

ACTIONS = [
    "s3:GetObject",
    "s3:GetBucket",
    "s3:PutObject",
    "s3:Get",
    "s3:*Object",
    "docs:read",
]

RESOURCES = [
    "docs/reports/q1.pdf",
    "docs/reports/",
    "docs/reportsQ1",
    "docs/public/readme.md",
    "docs/*/secret",
    "*",
]

PRINCIPALS = [
    "*",
    "user:alice",
    "user:bob",
    "user:al*",
    "role:dev",
    "role:oncall",
    "role:contractor",
    "role:admin",
    "USER:alice",
    "alice",
]

ACTION_PATTERNS = [
    "*",
    "s3:*",
    "s3:Get*",
    "s3:GetObject",
    "s3:PutObject",
    "s3:*Object",
    "s3:Get",
    "S3:Get*",
    "docs:read",
]

RESOURCE_PATTERNS = [
    "*",
    "docs/*",
    "docs/reports/*",
    "docs/reports/q1.pdf",
    "docs/reports",
    "docs/*/secret",
    "docs/reportsQ1",
    "DOCS/*",
]

BAD_EFFECTS = ["Allow", "allow", "Deny", "deny", "PERMIT", "ALLOW ", "", "NEUTRAL"]


def _hitting_principal(rng: random.Random, request: dict) -> str:
    """A principal drawn so that it matches this request."""
    candidates = ["*", "user:" + request["subject"]]
    candidates += ["role:" + role for role in request["roles"]]
    return rng.choice(candidates)


def _hitting_pattern(rng: random.Random, value: str) -> str:
    """A pattern drawn so that it matches ``value``, at a random specificity."""
    roll = rng.random()
    if roll < 0.25:
        return "*"
    if roll < 0.60:
        return value
    return value[: rng.randint(0, len(value))] + "*"


def _policy(rng: random.Random, request: dict) -> dict:
    roll = rng.random()
    if roll < 0.05:
        effect = rng.choice(BAD_EFFECTS)  # must make authorize() raise
    elif roll < 0.28:
        # DENY is deliberately the minority effect: under deny-overrides an
        # even split would make almost every sample come out DENY and the
        # ALLOW/DENY boundary -- where candidates actually differ -- would
        # hardly ever be probed.
        effect = "DENY"
    else:
        effect = "ALLOW"

    # Most fields are derived from the request so that policies genuinely
    # overlap; the rest come from the near-miss pools above.
    principal = (
        _hitting_principal(rng, request)
        if rng.random() < 0.75
        else rng.choice(PRINCIPALS)
    )
    action = (
        _hitting_pattern(rng, request["action"])
        if rng.random() < 0.70
        else rng.choice(ACTION_PATTERNS)
    )
    resource = (
        _hitting_pattern(rng, request["resource"])
        if rng.random() < 0.70
        else rng.choice(RESOURCE_PATTERNS)
    )
    return {
        "effect": effect,
        "principal": principal,
        "action": action,
        "resource": resource,
    }


def sample(rng: random.Random) -> tuple[tuple, dict]:
    request = {
        "subject": rng.choice(SUBJECTS),
        "roles": list(rng.choice(ROLE_SETS)),
        "action": rng.choice(ACTIONS),
        "resource": rng.choice(RESOURCES),
    }
    policies = [_policy(rng, request) for _ in range(rng.randint(0, 4))]

    if policies and rng.random() < 0.02:
        victim = rng.choice(policies)
        del victim[rng.choice(["effect", "principal", "action", "resource"])]
    elif rng.random() < 0.01:
        del request[rng.choice(["subject", "roles", "action", "resource"])]

    return (request, policies), {}


def _req(action: str = "s3:GetObject", resource: str = "docs/reports/q1.pdf", **kw) -> dict:
    base = {"subject": "alice", "roles": ["contractor"], "action": action, "resource": resource}
    base.update(kw)
    return base


# Inputs that are always tried first, before random sampling.  These encode the
# corners the specification calls out by name.
SEEDS: list[tuple[tuple, dict]] = [
    # No policies at all -> default deny.
    ((_req(), []), {}),
    # DENY listed AFTER the ALLOW.
    (
        (
            _req(),
            [
                {"effect": "ALLOW", "principal": "user:alice", "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
                {"effect": "DENY", "principal": "role:contractor", "action": "*", "resource": "docs/reports/*"},
            ],
        ),
        {},
    ),
    # The same pair with the DENY listed FIRST -- order must not matter.
    (
        (
            _req(),
            [
                {"effect": "DENY", "principal": "role:contractor", "action": "*", "resource": "docs/reports/*"},
                {"effect": "ALLOW", "principal": "user:alice", "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
            ],
        ),
        {},
    ),
    # Broadest possible DENY against the narrowest possible ALLOW.
    (
        (
            _req(),
            [
                {"effect": "ALLOW", "principal": "user:alice", "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
                {"effect": "DENY", "principal": "*", "action": "*", "resource": "*"},
            ],
        ),
        {},
    ),
    # A DENY whose principal does not match must be ignored entirely.
    (
        (
            _req(roles=["dev"]),
            [
                {"effect": "ALLOW", "principal": "role:dev", "action": "s3:Get*", "resource": "docs/*"},
                {"effect": "DENY", "principal": "role:contractor", "action": "*", "resource": "*"},
            ],
        ),
        {},
    ),
    # Trailing "*" is a prefix match and also matches the bare prefix itself.
    ((_req(action="s3:Get"), [{"effect": "ALLOW", "principal": "*", "action": "s3:Get*", "resource": "*"}]), {}),
    # Prefix match must respect the separator: "docs/reportsQ1" is not under it.
    (
        (
            _req(resource="docs/reportsQ1"),
            [{"effect": "ALLOW", "principal": "*", "action": "*", "resource": "docs/reports/*"}],
        ),
        {},
    ),
    # Interior "*" is a literal asterisk, so this pattern must NOT match.
    ((_req(), [{"effect": "ALLOW", "principal": "*", "action": "s3:*Object", "resource": "*"}]), {}),
    # ...and DOES match the action literally named "s3:*Object".
    ((_req(action="s3:*Object"), [{"effect": "ALLOW", "principal": "*", "action": "s3:*Object", "resource": "*"}]), {}),
    # Principals are not patterns: "user:al*" is a literal principal name.
    ((_req(), [{"effect": "ALLOW", "principal": "user:al*", "action": "*", "resource": "*"}]), {}),
    # Matching is case-sensitive.
    ((_req(), [{"effect": "ALLOW", "principal": "*", "action": "S3:Get*", "resource": "*"}]), {}),
    # Empty roles list, user-level ALLOW.
    ((_req(roles=[]), [{"effect": "ALLOW", "principal": "user:alice", "action": "*", "resource": "*"}]), {}),
    # Invalid: effect is case-sensitive.
    ((_req(), [{"effect": "Allow", "principal": "*", "action": "*", "resource": "*"}]), {}),
    # Invalid: unknown effect behind a policy that would already have denied.
    (
        (
            _req(),
            [
                {"effect": "DENY", "principal": "*", "action": "*", "resource": "*"},
                {"effect": "PERMIT", "principal": "*", "action": "*", "resource": "*"},
            ],
        ),
        {},
    ),
    # Invalid: policy missing a required field.
    ((_req(), [{"effect": "ALLOW", "principal": "*", "action": "*"}]), {}),
    # Invalid: request missing a required field.
    (({"subject": "alice", "roles": ["dev"], "action": "s3:GetObject"}, []), {}),
]
