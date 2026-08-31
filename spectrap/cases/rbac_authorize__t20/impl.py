def authorize(request: dict, policies: list[dict]) -> str:
    """
    Decide an access request against a policy set using deny-overrides (XACML 3.0).
    
    Returns "ALLOW" or "DENY".
    """
    # Validate request
    for field in ('subject', 'roles', 'action', 'resource'):
        if field not in request:
            raise ValueError(f"Request missing required field: {field}")
    
    if not isinstance(request['roles'], list):
        raise ValueError("Request 'roles' must be a list")
    
    # Validate all policies
    for policy in policies:
        for field in ('effect', 'principal', 'action', 'resource'):
            if field not in policy:
                raise ValueError(f"Policy missing required field: {field}")
        
        if policy['effect'] not in ('ALLOW', 'DENY'):
            raise ValueError(f"Policy effect must be 'ALLOW' or 'DENY', got '{policy['effect']}'")
    
    # Check policies using deny-overrides rule
    has_allow = False
    
    for policy in policies:
        if _policy_matches(request, policy):
            if policy['effect'] == 'DENY':
                return 'DENY'
            elif policy['effect'] == 'ALLOW':
                has_allow = True
    
    # Default deny unless we saw an ALLOW
    return 'ALLOW' if has_allow else 'DENY'


def _policy_matches(request: dict, policy: dict) -> bool:
    """Check if a policy matches the request."""
    return (
        _principal_matches(request, policy['principal']) and
        _pattern_matches(policy['action'], request['action']) and
        _pattern_matches(policy['resource'], request['resource'])
    )


def _principal_matches(request: dict, principal: str) -> bool:
    """Check if principal matches the request."""
    if principal == '*':
        return True
    
    if principal.startswith('user:'):
        user_part = principal[5:]
        return user_part == request['subject']
    
    if principal.startswith('role:'):
        role_part = principal[5:]
        return role_part in request['roles']
    
    return False


def _pattern_matches(pattern: str, value: str) -> bool:
    """Check if a pattern matches a value. Pattern can have trailing * as wildcard."""
    if pattern == '*':
        return True
    
    if pattern.endswith('*'):
        prefix = pattern[:-1]
        return value.startswith(prefix)
    
    return pattern == value
