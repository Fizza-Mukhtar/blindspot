def authorize(request: dict, policies: list[dict]) -> str:
    """
    Decide access requests against a policy set using XACML deny-overrides.
    
    Args:
        request: dict with keys subject, roles (list), action, resource
        policies: list of dicts with keys effect, principal, action, resource
        
    Returns:
        "ALLOW" or "DENY"
        
    Raises:
        ValueError: if request or policies are invalid
    """
    # Validate request
    _validate_request(request)
    
    # Validate policies
    _validate_policies(policies)
    
    # Find matching policies and apply deny-overrides algorithm
    has_matching_deny = False
    has_matching_allow = False
    
    for policy in policies:
        if _policy_matches(request, policy):
            if policy['effect'] == 'DENY':
                has_matching_deny = True
                break  # Any matching DENY decides the outcome
            elif policy['effect'] == 'ALLOW':
                has_matching_allow = True
    
    # Apply deny-overrides algorithm: DENY > ALLOW > default DENY
    if has_matching_deny:
        return "DENY"
    elif has_matching_allow:
        return "ALLOW"
    else:
        return "DENY"  # Default deny


def _validate_request(request: dict) -> None:
    """Validate the request dict has all required fields."""
    required_keys = ['subject', 'roles', 'action', 'resource']
    
    for key in required_keys:
        if key not in request:
            raise ValueError(f"Request missing key: {key}")
    
    if not isinstance(request['roles'], list):
        raise ValueError("roles must be a list")


def _validate_policies(policies: list[dict]) -> None:
    """Validate all policies have required fields and valid effects."""
    required_keys = ['effect', 'principal', 'action', 'resource']
    
    for policy in policies:
        for key in required_keys:
            if key not in policy:
                raise ValueError(f"Policy missing key: {key}")
        
        effect = policy['effect']
        if effect not in ('ALLOW', 'DENY'):
            raise ValueError(f"Invalid effect: {effect}")


def _policy_matches(request: dict, policy: dict) -> bool:
    """Check if all components of a policy match the request."""
    return (
        _principal_matches(request, policy['principal']) and
        _pattern_matches(request['action'], policy['action']) and
        _pattern_matches(request['resource'], policy['resource'])
    )


def _principal_matches(request: dict, principal: str) -> bool:
    """Check if a principal (subject, role, or wildcard) matches the request."""
    if principal == '*':
        return True
    
    if principal.startswith('user:'):
        user = principal[5:]
        return user == request['subject']
    
    if principal.startswith('role:'):
        role = principal[5:]
        return role in request['roles']
    
    return False


def _pattern_matches(value: str, pattern: str) -> bool:
    """
    Check if a value matches a pattern.
    
    Patterns support one piece of syntax: a trailing *.
    'prefix*' matches any value starting with 'prefix'.
    '*' matches any value.
    Otherwise, the pattern must match exactly.
    """
    if pattern == '*':
        return True
    
    if pattern.endswith('*'):
        prefix = pattern[:-1]
        return value.startswith(prefix)
    
    return value == pattern
