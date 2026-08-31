"""Reference implementation for IAM-2287 (policy-set access decision).

Hidden from every system under evaluation.  Used only by the grader, to decide
whether a generated counterexample is *sound*: a test that fails on the
candidate must pass here, or the test is wrong rather than the code.

Authority: XACML 3.0 core specification, the deny-overrides rule-combining
algorithm (Appendix C.2) --
https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html
The same combining rule governs AWS IAM identity-policy evaluation.
"""

from __future__ import annotations

_EFFECTS = frozenset({"ALLOW", "DENY"})
_REQUEST_FIELDS = ("subject", "roles", "action", "resource")
_POLICY_FIELDS = ("effect", "principal", "action", "resource")


def _pattern_matches(pattern: str, value: str) -> bool:
    """Trailing-``*`` prefix match, exact match otherwise.

    The only wildcard is a final ``*``; the bare pattern ``"*"`` falls out of
    the same rule as the empty prefix.  A ``*`` anywhere else is a literal
    asterisk, so ``"s3:*Object"`` matches only the action of that exact name.
    """
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def _principal_matches(principal: str, subject: str, roles: list[str]) -> bool:
    """Principals are exact strings, never patterns; only bare ``*`` is open."""
    if principal == "*":
        return True
    if principal == "user:" + subject:
        return True
    return any(principal == "role:" + role for role in roles)


def _validate(request: dict, policies: list[dict]) -> None:
    """Full validation pass, run before any policy is evaluated."""
    for field in _REQUEST_FIELDS:
        if field not in request:
            raise ValueError(f"request is missing required field {field!r}")
    if not isinstance(request["roles"], list):
        raise ValueError("request field 'roles' must be a list of role names")

    for index, policy in enumerate(policies):
        for field in _POLICY_FIELDS:
            if field not in policy:
                raise ValueError(
                    f"policy at index {index} is missing required field {field!r}"
                )
        effect = policy["effect"]
        if effect not in _EFFECTS:
            # Case-sensitive: "Allow"/"allow" are typos, not effects.
            raise ValueError(f"policy at index {index} has unknown effect: {effect!r}")


def authorize(request: dict, policies: list[dict]) -> str:
    """Return "ALLOW" or "DENY" for ``request`` under ``policies``."""
    _validate(request, policies)

    subject: str = request["subject"]
    roles: list[str] = request["roles"]
    action: str = request["action"]
    resource: str = request["resource"]

    seen_allow = False
    for policy in policies:
        if not _principal_matches(policy["principal"], subject, roles):
            continue
        if not _pattern_matches(policy["action"], action):
            continue
        if not _pattern_matches(policy["resource"], resource):
            continue
        if policy["effect"] == "DENY":
            # deny-overrides: a single matching DENY settles it, whatever else
            # matched, wherever it sat in the list, however specific it was.
            return "DENY"
        seen_allow = True

    # Default deny (XACML NotApplicable -> DENY at the PEP): no matching ALLOW.
    return "ALLOW" if seen_allow else "DENY"
