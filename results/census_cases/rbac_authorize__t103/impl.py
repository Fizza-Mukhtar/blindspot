"""IAM access control decision function using deny-overrides."""


def authorize(request: dict, policies: list[dict]) -> str:
    """
    Decide access requests against a policy set using deny-overrides.
    
    Args:
        request: Dict with fields subject, roles (list), action, resource
        policies: List of policy dicts with fields effect, principal, action, resource
    
    Returns:
        "ALLOW" or "DENY"
    
    Raises:
        ValueError: If request or any policy is invalid
    """
    _validate_request(request)
    for policy in policies:
        _validate_policy(policy)
    
    for policy in policies:
        if policy["effect"] == "DENY" and _policy_matches(request, policy):
            return "DENY"
    
    for policy in policies:
        if policy["effect"] == "ALLOW" and _policy_matches(request, policy):
            return "ALLOW"
    
    return "DENY"


def _validate_request(request: dict) -> None:
    """Validate request has required fields and correct types."""
    required = {"subject", "roles", "action", "resource"}
    missing = required - set(request.keys())
    if missing:
        raise ValueError(f"Request missing required field(s): {', '.join(sorted(missing))}")
    
    if not isinstance(request["roles"], list):
        raise ValueError("Request 'roles' must be a list")


def _validate_policy(policy: dict) -> None:
    """Validate policy has required fields and valid effect."""
    required = {"effect", "principal", "action", "resource"}
    missing = required - set(policy.keys())
    if missing:
        raise ValueError(f"Policy missing required field(s): {', '.join(sorted(missing))}")
    
    effect = policy["effect"]
    if effect not in ("ALLOW", "DENY"):
        raise ValueError(f"Policy 'effect' must be 'ALLOW' or 'DENY', got '{effect}'")


def _policy_matches(request: dict, policy: dict) -> bool:
    """Check if a policy matches the request."""
    return (_principal_matches(request, policy["principal"]) and
            _action_matches(request["action"], policy["action"]) and
            _resource_matches(request["resource"], policy["resource"]))


def _principal_matches(request: dict, principal: str) -> bool:
    """Check if principal matches the request."""
    if principal == "*":
        return True
    
    if principal.startswith("user:"):
        return principal[5:] == request["subject"]
    
    if principal.startswith("role:"):
        role_name = principal[5:]
        return role_name in request["roles"]
    
    return False


def _action_matches(request_action: str, policy_action: str) -> bool:
    """Check if policy action pattern matches request action."""
    if policy_action == "*":
        return True
    
    if policy_action.endswith("*"):
        prefix = policy_action[:-1]
        return request_action.startswith(prefix)
    
    return request_action == policy_action


def _resource_matches(request_resource: str, policy_resource: str) -> bool:
    """Check if policy resource pattern matches request resource."""
    if policy_resource == "*":
        return True
    
    if policy_resource.endswith("*"):
        prefix = policy_resource[:-1]
        return request_resource.startswith(prefix)
    
    return request_resource == policy_resource
