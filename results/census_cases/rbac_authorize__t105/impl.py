def authorize(request: dict, policies: list[dict]) -> str:
    """
    Decide access requests against the policy set using deny-overrides (XACML).
    
    Args:
        request: Must contain 'subject', 'roles' (list), 'action', 'resource'
        policies: List of policies, each with 'effect', 'principal', 'action', 'resource'
    
    Returns:
        "ALLOW" or "DENY"
    
    Raises:
        ValueError: If request or any policy is invalid
    """
    
    # Validate request
    required_request_fields = {'subject', 'roles', 'action', 'resource'}
    missing_fields = required_request_fields - set(request.keys())
    if missing_fields:
        raise ValueError(f"Request missing field(s): {', '.join(sorted(missing_fields))}")
    
    if not isinstance(request['roles'], list):
        raise ValueError("Request 'roles' must be a list")
    
    # Validate all policies before deciding
    required_policy_fields = {'effect', 'principal', 'action', 'resource'}
    for policy in policies:
        missing_fields = required_policy_fields - set(policy.keys())
        if missing_fields:
            raise ValueError(f"Policy missing field(s): {', '.join(sorted(missing_fields))}")
        
        if policy['effect'] not in ('ALLOW', 'DENY'):
            raise ValueError(f"Policy has invalid effect: {policy['effect']!r}")
    
    # Apply deny-overrides logic
    deny_found = False
    allow_found = False
    
    for policy in policies:
        if _policy_matches(request, policy):
            if policy['effect'] == 'DENY':
                deny_found = True
            elif policy['effect'] == 'ALLOW':
                allow_found = True
    
    if deny_found:
        return "DENY"
    elif allow_found:
        return "ALLOW"
    else:
        return "DENY"  # Default deny


def _policy_matches(request: dict, policy: dict) -> bool:
    """Check if a policy matches the request."""
    return (_principal_matches(request, policy['principal']) and
            _pattern_matches(request['action'], policy['action']) and
            _pattern_matches(request['resource'], policy['resource']))


def _principal_matches(request: dict, principal: str) -> bool:
    """Check if principal matches the request."""
    if principal == "*":
        return True
    
    if principal.startswith("user:"):
        return principal[5:] == request['subject']
    
    if principal.startswith("role:"):
        role = principal[5:]
        return role in request['roles']
    
    return False


def _pattern_matches(value: str, pattern: str) -> bool:
    """Check if value matches pattern with trailing * for prefix matching."""
    if pattern == "*":
        return True
    
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return value.startswith(prefix)
    
    return value == pattern
