def authorize(request: dict, policies: list[dict]) -> str:
    """Decide ALLOW or DENY for an access request against a policy set.

    Applies the XACML-style deny-overrides combining algorithm: any matching
    DENY policy wins outright; otherwise any matching ALLOW policy wins;
    otherwise the request is denied by default. Neither argument is mutated.
    """
    required_request_fields = ("subject", "roles", "action", "resource")
    missing_request_fields = [
        field for field in required_request_fields if field not in request
    ]
    if missing_request_fields:
        raise ValueError(
            f"request is missing required field(s): {missing_request_fields}"
        )
    if not isinstance(request["roles"], list):
        raise ValueError("request['roles'] must be a list")

    required_policy_fields = ("effect", "principal", "action", "resource")
    for index, policy in enumerate(policies):
        missing_policy_fields = [
            field for field in required_policy_fields if field not in policy
        ]
        if missing_policy_fields:
            raise ValueError(
                f"policy at index {index} is missing required field(s): "
                f"{missing_policy_fields}"
            )
        if policy["effect"] not in ("ALLOW", "DENY"):
            raise ValueError(
                f"policy at index {index} has invalid effect: {policy['effect']!r}"
            )

    subject = request["subject"]
    roles = request["roles"]
    action = request["action"]
    resource = request["resource"]

    def principal_matches(principal: str) -> bool:
        if principal == "*":
            return True
        if principal == f"user:{subject}":
            return True
        if principal.startswith("role:") and principal[len("role:"):] in roles:
            return True
        return False

    def pattern_matches(pattern: str, value: str) -> bool:
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return pattern == value

    matched_effects = set()
    for policy in policies:
        if (
            principal_matches(policy["principal"])
            and pattern_matches(policy["action"], action)
            and pattern_matches(policy["resource"], resource)
        ):
            matched_effects.add(policy["effect"])

    if "DENY" in matched_effects:
        return "DENY"
    if "ALLOW" in matched_effects:
        return "ALLOW"
    return "DENY"
