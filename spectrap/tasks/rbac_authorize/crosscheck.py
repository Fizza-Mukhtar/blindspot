"""Independent oracle for IAM-2287 (`authorize`).

Written from SPEC.md plus XACML 3.0 core spec, Appendix C.2 (deny-overrides),
WITHOUT looking at reference.py or selftest.py.
"""

from __future__ import annotations

import re

ORACLE_NOTES = """\
Independent re-derivation from SPEC.md + OASIS XACML 3.0 core spec App. C.2
(deny-overrides): "if a single <Rule> ... evaluates to 'Deny', then, regardless
of the evaluation result of the other <Rule> ... elements, the combined result
is 'Deny'"; NotApplicable when nothing applies, which this ticket maps to the
PEP-side default deny. Clauses checked: C.2 deny-overrides (Deny dominates
Permit unconditionally; XACML has no specificity tie-break and no order
sensitivity -- first-applicable is a separate, differently named algorithm);
NotApplicable -> DENY (SPEC.md rule 3, incl. the empty list); XACML
string-equal is codepoint equality -> case-sensitive throughout.

Deliberately different structure from the obvious loop-and-return:
(1) validation is a separate exhaustive pass over the request and EVERY policy;
(2) action/resource matching delegates to the stdlib `re` module -- a pattern
    is compiled to re.escape(p[:-1]) + ".*" when its LAST char is "*", else
    re.escape(p), matched with re.fullmatch. re.escape is what makes an
    interior "*" a literal asterisk and kills ?/[...]/regex metacharacters;
    the opposite reach from fnmatch, which would honour an interior "*";
(3) principals are set membership in {"*","user:"+subject} u {"role:"+r ...};
(4) combining is a literal decision TABLE keyed by (any DENY, any ALLOW), so
    order-independence is structural, plus a reversed-order self-assertion.

Under-determined in SPEC.md (reported, not claimed as defects): the meaning of
an EMPTY pattern "" (no last character -> treated here as an exact match);
which of request-malformed vs policy-malformed is reported when both hold
(both ValueError, so only the message differs; request first here); extra keys
and non-string field values (task.yaml's own open questions -- ignored / not
type-checked here except `roles` must be a list; a non-string `subject` makes
this oracle raise TypeError while an implementation that tests principal == "*"
before building "user:"+subject returns a decision -- both readings are legal,
the input is outside the generator's domain). Mapping XACML NotApplicable
onto "DENY" is a PEP decision rather than part of C.2, but SPEC.md states that
narrowing explicitly, so it is not a defect.
"""

_ALLOW = "ALLOW"
_DENY = "DENY"
_VALID_EFFECTS = ("ALLOW", "DENY")  # exact, case-sensitive
_REQUEST_FIELDS = ("subject", "roles", "action", "resource")
_POLICY_FIELDS = ("effect", "principal", "action", "resource")

# Combining decision table, keyed by (a matching DENY exists, a matching ALLOW
# exists).  XACML 3.0 App. C.2 deny-overrides.  Being a table rather than
# control flow, it cannot accidentally depend on list order or specificity.
_COMBINE = {
    (True, True): _DENY,   # C.2: Deny wins regardless of the other results
    (True, False): _DENY,  # C.2: Deny
    (False, True): _ALLOW,  # only Permits -> Permit
    (False, False): _DENY,  # NotApplicable -> default deny (SPEC.md rule 3)
}


def _compile(pattern: str) -> "re.Pattern[str]":
    """Compile SPEC.md's one-piece-of-syntax pattern grammar into a regex.

    `re.escape` neutralises every metacharacter, so an interior `*` stays a
    literal asterisk and `?` / `[...]` are literals too.  Only a *final* `*`
    becomes a wildcard, and it becomes `.*` (with DOTALL) i.e. a prefix match
    that also admits the bare prefix.
    """
    if pattern.endswith("*"):
        return re.compile(re.escape(pattern[:-1]) + ".*", re.DOTALL)
    return re.compile(re.escape(pattern), re.DOTALL)


def _pattern_matches(pattern: str, value: str) -> bool:
    return _compile(pattern).fullmatch(value) is not None


def _validate(request, policies) -> None:
    """Exhaustive validation pass; runs to completion before any deciding."""
    if not isinstance(request, dict):
        raise ValueError("request must be a dict")
    for field in _REQUEST_FIELDS:
        if field not in request:
            raise ValueError("request is missing required field %r" % (field,))
    if not isinstance(request["roles"], list):
        raise ValueError("request field 'roles' must be a list")

    if not isinstance(policies, (list, tuple)):
        raise ValueError("policies must be a list")
    for index, policy in enumerate(policies):
        if not isinstance(policy, dict):
            raise ValueError("policy %d is not a dict" % index)
        for field in _POLICY_FIELDS:
            if field not in policy:
                raise ValueError(
                    "policy %d is missing required field %r" % (index, field)
                )
        effect = policy["effect"]
        if not (isinstance(effect, str) and effect in _VALID_EFFECTS):
            # The message must contain the offending value verbatim.
            raise ValueError(
                "policy %d has invalid effect %s (expected exactly 'ALLOW' or "
                "'DENY')" % (index, effect)
            )


def _matching_effects(request, policies) -> list:
    """Effects of the policies that match the request, in list order."""
    # A principal is not a pattern: it is one of a finite set of literals.
    principals = {"*", "user:" + request["subject"]}
    principals.update("role:" + role for role in request["roles"])

    action = request["action"]
    resource = request["resource"]

    effects = []
    for policy in policies:
        if policy["principal"] not in principals:
            continue
        if not _pattern_matches(policy["action"], action):
            continue
        if not _pattern_matches(policy["resource"], resource):
            continue
        effects.append(policy["effect"])
    return effects


def _decide(effects) -> str:
    seen = set(effects)
    return _COMBINE[(_DENY in seen, _ALLOW in seen)]


def oracle(request, policies) -> str:
    _validate(request, policies)
    effects = _matching_effects(request, policies)
    decision = _decide(effects)
    # Redundant order-independence self-check (XACML C.2 is order free).
    assert decision == _decide(list(reversed(effects))), "order dependence!"
    return decision


authorize = oracle


def _r(subject, roles, action, resource):
    return {
        "subject": subject,
        "roles": list(roles),
        "action": action,
        "resource": resource,
    }


def _p(effect, principal, action, resource):
    return {
        "effect": effect,
        "principal": principal,
        "action": action,
        "resource": resource,
    }


KNOWN_VALUES: list = [
    # 1. SPEC.md's own worked example: role-level DENY beats a later, narrower,
    #    user-level ALLOW.  XACML C.2: Deny regardless of the other results.
    (
        (
            _r("alice", ["contractor"], "s3:GetObject", "docs/reports/q1.pdf"),
            [
                _p("DENY", "role:contractor", "*", "docs/reports/*"),
                _p("ALLOW", "user:alice", "s3:GetObject", "docs/reports/q1.pdf"),
            ],
        ),
        {},
        "DENY",
    ),
    # 2. Same pair reversed -> still DENY (C.2 is order independent).
    (
        (
            _r("alice", ["contractor"], "s3:GetObject", "docs/reports/q1.pdf"),
            [
                _p("ALLOW", "user:alice", "s3:GetObject", "docs/reports/q1.pdf"),
                _p("DENY", "role:contractor", "*", "docs/reports/*"),
            ],
        ),
        {},
        "DENY",
    ),
    # 3. No policies -> NotApplicable -> default deny (SPEC.md rule 3).
    (
        (_r("alice", ["dev"], "s3:GetObject", "docs/reports/q1.pdf"), []),
        {},
        "DENY",
    ),
    # 4. Only Permits apply -> Permit (C.2 second branch).
    (
        (
            _r("alice", ["dev"], "s3:GetObject", "docs/reports/q1.pdf"),
            [
                _p("ALLOW", "role:dev", "s3:Get*", "docs/*"),
                _p("DENY", "role:contractor", "*", "*"),  # principal misses
            ],
        ),
        {},
        "ALLOW",
    ),
    # 5. Trailing '*' matches the bare prefix itself ("s3:Get*" vs "s3:Get").
    (
        (
            _r("alice", [], "s3:Get", "docs/reports/q1.pdf"),
            [_p("ALLOW", "*", "s3:Get*", "*")],
        ),
        {},
        "ALLOW",
    ),
    # 6. Prefix match is literal: "docs/reports/*" does not cover
    #    "docs/reportsQ1" -> nothing matches -> DENY.
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reportsQ1"),
            [_p("ALLOW", "*", "*", "docs/reports/*")],
        ),
        {},
        "DENY",
    ),
    # 7. Interior '*' is a LITERAL asterisk: "s3:*Object" does not match
    #    "s3:GetObject".
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [_p("ALLOW", "*", "s3:*Object", "*")],
        ),
        {},
        "DENY",
    ),
    # 8. ...and it DOES match the action literally named "s3:*Object".
    (
        (
            _r("alice", [], "s3:*Object", "docs/reports/q1.pdf"),
            [_p("ALLOW", "*", "s3:*Object", "*")],
        ),
        {},
        "ALLOW",
    ),
    # 9. A principal is never a pattern: "user:al*" is the literal name "al*".
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [_p("ALLOW", "user:al*", "*", "*")],
        ),
        {},
        "DENY",
    ),
    # 10. Case-sensitive matching (XACML string-equal is codepoint equality).
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [_p("ALLOW", "*", "S3:Get*", "*")],
        ),
        {},
        "DENY",
    ),
    # 11. Broadest DENY beats narrowest ALLOW: no specificity tie-break exists.
    (
        (
            _r("alice", ["dev"], "s3:GetObject", "docs/reports/q1.pdf"),
            [
                _p("ALLOW", "user:alice", "s3:GetObject", "docs/reports/q1.pdf"),
                _p("DENY", "*", "*", "*"),
            ],
        ),
        {},
        "DENY",
    ),
    # 12. Effect is case-sensitive: "Allow" is invalid, not a non-match.
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [_p("Allow", "*", "*", "*")],
        ),
        {},
        ("raises", "ValueError"),
    ),
    # 13. Validation runs over EVERY policy, even behind a decisive DENY.
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [
                _p("DENY", "*", "*", "*"),
                _p("PERMIT", "*", "*", "*"),
            ],
        ),
        {},
        ("raises", "ValueError"),
    ),
    # 14. Policy missing a required field.
    (
        (
            _r("alice", [], "s3:GetObject", "docs/reports/q1.pdf"),
            [{"effect": "ALLOW", "principal": "*", "action": "*"}],
        ),
        {},
        ("raises", "ValueError"),
    ),
    # 15. Request missing a required field.
    (
        ({"subject": "alice", "roles": ["dev"], "action": "s3:GetObject"}, []),
        {},
        ("raises", "ValueError"),
    ),
    # 16. roles present but not a list.
    (
        (
            {
                "subject": "alice",
                "roles": "dev",
                "action": "s3:GetObject",
                "resource": "docs/reports/q1.pdf",
            },
            [],
        ),
        {},
        ("raises", "ValueError"),
    ),
]
