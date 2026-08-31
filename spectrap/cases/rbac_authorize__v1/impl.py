def _match_pattern(pattern: str, value: str) -> bool:
    """Match a value against a pattern with optional trailing '*' wildcard."""
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return value == pattern


def _match_principal(principal: str, subject: str, roles: list[str]) -> bool:
    """Match a policy principal against the request's subject/roles."""
    if principal == "*":
        return True
    if principal == f"user:{subject}":
        return True
    if principal.startswith("role:") and principal[len("role:"):] in roles:
        return True
    return False


def authorize(request: dict, policies: list[dict]) -> str:
    """Decide ALLOW/DENY for a request against a policy set using deny-overrides.

    Neither `request` nor `policies` is mutated.
    """
    required_request_fields = ("subject", "roles", "action", "resource")
    for field in required_request_fields:
        if field not in request:
            raise ValueError(f"request is missing required field '{field}'")
    if not isinstance(request["roles"], list):
        raise ValueError("request field 'roles' must be a list")

    required_policy_fields = ("effect", "principal", "action", "resource")
    for policy in policies:
        for field in required_policy_fields:
            if field not in policy:
                raise ValueError(f"policy is missing required field '{field}'")
        if policy["effect"] not in ("ALLOW", "DENY"):
            raise ValueError(f"invalid policy effect: {policy['effect']!r}")

    subject = request["subject"]
    roles = request["roles"]
    action = request["action"]
    resource = request["resource"]

    has_allow = False
    for policy in policies:
        if not _match_principal(policy["principal"], subject, roles):
            continue
        if not _match_pattern(policy["action"], action):
            continue
        if not _match_pattern(policy["resource"], resource):
            continue
        if policy["effect"] == "DENY":
            return "DENY"
        has_allow = True

    return "ALLOW" if has_allow else "DENY"
