def authorize(request: dict, policies: list[dict]) -> str:
    """
    Authorize a request against a set of policies.
    
    Returns "ALLOW" or "DENY" based on XACML deny-overrides rule-combining algorithm.
    """
    
    # Validate request
    required_request_fields = {'subject', 'roles', 'action', 'resource'}
    for field in required_request_fields:
        if field not in request:
            raise ValueError(f"Request missing field: {field}")
    
    if not isinstance(request['roles'], list):
        raise ValueError("Request 'roles' must be a list")
    
    # Validate policies
    for policy in policies:
        required_policy_fields = {'effect', 'principal', 'action', 'resource'}
        for field in required_policy_fields:
            if field not in policy:
                raise ValueError(f"Policy missing field: {field}")
        
        effect = policy['effect']
        if effect not in ('ALLOW', 'DENY'):
            raise ValueError(f"Policy effect must be 'ALLOW' or 'DENY', got {effect!r}")
    
    # Extract request values
    subject = request['subject']
    roles = request['roles']
    request_action = request['action']
    request_resource = request['resource']
    
    # Helper function to check if a principal matches
    def principal_matches(principal: str) -> bool:
        if principal == "*":
            return True
        if principal.startswith("user:"):
            return principal == f"user:{subject}"
        if principal.startswith("role:"):
            role_name = principal[5:]  # Remove "role:" prefix
            return role_name in roles
        return False
    
    # Helper function to check if an action pattern matches
    def action_matches(pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return request_action.startswith(prefix)
        return pattern == request_action
    
    # Helper function to check if a resource pattern matches
    def resource_matches(pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return request_resource.startswith(prefix)
        return pattern == request_resource
    
    # Check policies using XACML deny-overrides algorithm
    # First pass: any matching DENY gives DENY
    for policy in policies:
        if (policy['effect'] == 'DENY' and
            principal_matches(policy['principal']) and
            action_matches(policy['action']) and
            resource_matches(policy['resource'])):
            return "DENY"
    
    # Second pass: any matching ALLOW gives ALLOW
    for policy in policies:
        if (policy['effect'] == 'ALLOW' and
            principal_matches(policy['principal']) and
            action_matches(policy['action']) and
            resource_matches(policy['resource'])):
            return "ALLOW"
    
    # Default deny: no matching policy found
    return "DENY"
