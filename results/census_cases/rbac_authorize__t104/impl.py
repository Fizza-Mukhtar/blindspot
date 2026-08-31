def authorize(request: dict, policies: list[dict]) -> str:
    """Decide access against a policy set using XACML deny-overrides.
    
    Returns "ALLOW" or "DENY".
    """
    
    # Validate request
    required_request_fields = {'subject', 'roles', 'action', 'resource'}
    if not all(field in request for field in required_request_fields):
        missing = required_request_fields - set(request.keys())
        raise ValueError(f"Request missing required fields: {missing}")
    
    if not isinstance(request['roles'], list):
        raise ValueError("Request 'roles' must be a list")
    
    # Validate all policies
    required_policy_fields = {'effect', 'principal', 'action', 'resource'}
    for i, policy in enumerate(policies):
        if not all(field in policy for field in required_policy_fields):
            missing = required_policy_fields - set(policy.keys())
            raise ValueError(f"Policy {i} missing required fields: {missing}")
        
        effect = policy['effect']
        if effect not in ('ALLOW', 'DENY'):
            raise ValueError(f"Policy {i} has invalid effect: {effect}")
    
    # Check for matching DENY policies (deny-overrides)
    for policy in policies:
        if policy['effect'] == 'DENY' and _matches_policy(request, policy):
            return 'DENY'
    
    # Check for matching ALLOW policies
    for policy in policies:
        if policy['effect'] == 'ALLOW' and _matches_policy(request, policy):
            return 'ALLOW'
    
    # Default deny
    return 'DENY'


def _matches_policy(request: dict, policy: dict) -> bool:
    """Check if a policy matches a request."""
    return (_matches_principal(request, policy['principal']) and
            _matches_pattern(request['action'], policy['action']) and
            _matches_pattern(request['resource'], policy['resource']))


def _matches_principal(request: dict, principal: str) -> bool:
    """Check if a principal matches the request."""
    if principal == '*':
        return True
    
    if principal.startswith('user:'):
        return principal[5:] == request['subject']
    
    if principal.startswith('role:'):
        role = principal[5:]
        return role in request['roles']
    
    return False


def _matches_pattern(value: str, pattern: str) -> bool:
    """Check if a value matches a pattern (with optional trailing *)."""
    if pattern == '*':
        return True
    
    if pattern.endswith('*'):
        prefix = pattern[:-1]
        return value.startswith(prefix)
    
    return value == pattern
