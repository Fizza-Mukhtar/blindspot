import pytest
import impl


def test_simple_allow():
    """Basic ALLOW decision."""
    request = {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    assert impl.authorize(request, policies) == 'ALLOW'


def test_simple_deny():
    """Basic DENY decision."""
    request = {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}
    policies = [{'effect': 'DENY', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    assert impl.authorize(request, policies) == 'DENY'


def test_deny_overrides_allow():
    """DENY policy overrides ALLOW regardless of order."""
    request = {'subject': 'alice', 'roles': ['contractor'], 'action': 'docs:Read', 'resource': 'docs/reports/Q1.pdf'}
    policies = [
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/*'},
        {'effect': 'DENY', 'principal': 'role:contractor', 'action': 'docs:Read', 'resource': 'docs/reports/*'}
    ]
    assert impl.authorize(request, policies) == 'DENY'


def test_deny_overrides_regardless_of_position():
    """DENY policy wins even if listed first."""
    request = {'subject': 'alice', 'roles': ['contractor'], 'action': 'docs:Read', 'resource': 'docs/reports/Q1.pdf'}
    policies = [
        {'effect': 'DENY', 'principal': 'role:contractor', 'action': 'docs:Read', 'resource': 'docs/reports/*'},
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/*'}
    ]
    assert impl.authorize(request, policies) == 'DENY'


def test_action_pattern_matching():
    """Action patterns: exact match, prefix with *, and wildcard."""
    # Exact match
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/key'}]
    ) == 'ALLOW'
    
    # Prefix match with *
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get*', 'resource': 'bucket/key'}]
    ) == 'ALLOW'
    
    # No match
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:PutObject', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get*', 'resource': 'bucket/key'}]
    ) == 'DENY'
    
    # Wildcard
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'any:Action', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': '*', 'resource': 'bucket/key'}]
    ) == 'ALLOW'


def test_resource_pattern_matching():
    """Resource patterns: exact match, prefix with *, wildcard."""
    # Exact match
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'docs:Read', 'resource': 'docs/reports/Q1.pdf'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/Q1.pdf'}]
    ) == 'ALLOW'
    
    # Prefix match
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'docs:Read', 'resource': 'docs/reports/Q1.pdf'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/*'}]
    ) == 'ALLOW'
    
    # No match
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'docs:Read', 'resource': 'docs/reportsQ1'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/*'}]
    ) == 'DENY'
    
    # Wildcard
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'docs:Read', 'resource': 'any/path'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': '*'}]
    ) == 'ALLOW'


def test_principal_matching():
    """Principal matching: user, role, wildcard."""
    # User principal
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    ) == 'ALLOW'
    
    # User no match
    assert impl.authorize(
        {'subject': 'bob', 'roles': [], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    ) == 'DENY'
    
    # Role principal
    assert impl.authorize(
        {'subject': 'alice', 'roles': ['analyst'], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'role:analyst', 'action': 'read', 'resource': 'data'}]
    ) == 'ALLOW'
    
    # Role no match
    assert impl.authorize(
        {'subject': 'alice', 'roles': ['user'], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'role:admin', 'action': 'read', 'resource': 'data'}]
    ) == 'DENY'
    
    # Wildcard principal
    assert impl.authorize(
        {'subject': 'anyone', 'roles': [], 'action': 'public:Read', 'resource': 'public/data'},
        [{'effect': 'ALLOW', 'principal': '*', 'action': 'public:Read', 'resource': 'public/data'}]
    ) == 'ALLOW'


def test_default_deny():
    """No matching policies or empty policies list should deny."""
    # Empty policies
    assert impl.authorize({'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}, []) == 'DENY'
    
    # No matching policies
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'user:bob', 'action': 'write', 'resource': 'other'}]
    ) == 'DENY'


def test_validation_request_fields():
    """Request must have all required fields."""
    # Missing subject
    with pytest.raises(ValueError, match="subject"):
        impl.authorize({'roles': [], 'action': 'read', 'resource': 'data'}, [])
    
    # Missing roles
    with pytest.raises(ValueError, match="roles"):
        impl.authorize({'subject': 'alice', 'action': 'read', 'resource': 'data'}, [])
    
    # Missing action
    with pytest.raises(ValueError, match="action"):
        impl.authorize({'subject': 'alice', 'roles': [], 'resource': 'data'}, [])
    
    # Missing resource
    with pytest.raises(ValueError, match="resource"):
        impl.authorize({'subject': 'alice', 'roles': [], 'action': 'read'}, [])


def test_validation_roles_not_list():
    """Request roles must be a list."""
    with pytest.raises(ValueError, match="must be a list"):
        impl.authorize({'subject': 'alice', 'roles': 'analyst', 'action': 'read', 'resource': 'data'}, [])


def test_validation_policy_fields():
    """Policies must have all required fields."""
    request = {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}
    
    # Missing effect
    with pytest.raises(ValueError, match="effect"):
        impl.authorize(request, [{'principal': 'user:alice', 'action': 'read', 'resource': 'data'}])
    
    # Missing principal
    with pytest.raises(ValueError, match="principal"):
        impl.authorize(request, [{'effect': 'ALLOW', 'action': 'read', 'resource': 'data'}])
    
    # Missing action
    with pytest.raises(ValueError, match="action"):
        impl.authorize(request, [{'effect': 'ALLOW', 'principal': 'user:alice', 'resource': 'data'}])
    
    # Missing resource
    with pytest.raises(ValueError, match="resource"):
        impl.authorize(request, [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read'}])


def test_validation_invalid_effect():
    """Effect must be exactly ALLOW or DENY."""
    request = {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}
    
    # Lowercase
    with pytest.raises(ValueError, match="Allow"):
        impl.authorize(request, [{'effect': 'Allow', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}])
    
    # Typo
    with pytest.raises(ValueError, match="PERMIT"):
        impl.authorize(request, [{'effect': 'PERMIT', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}])


def test_validation_all_policies_before_decision():
    """All policies validated before any decision made."""
    request = {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'}
    policies = [
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'},
        {'effect': 'INVALID', 'principal': 'user:bob', 'action': 'read', 'resource': 'data'}
    ]
    # Should raise error for invalid effect despite first policy matching
    with pytest.raises(ValueError, match="INVALID"):
        impl.authorize(request, policies)


def test_case_sensitivity():
    """Matching is case-sensitive."""
    # Action case sensitive
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:getobject', 'resource': 'bucket/key'}]
    ) == 'DENY'
    
    # Resource case sensitive
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'Docs/Reports/Q1.pdf'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'docs/reports/Q1.pdf'}]
    ) == 'DENY'
    
    # Subject case sensitive
    assert impl.authorize(
        {'subject': 'Alice', 'roles': [], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    ) == 'DENY'
    
    # Role case sensitive
    assert impl.authorize(
        {'subject': 'alice', 'roles': ['Analyst'], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'role:analyst', 'action': 'read', 'resource': 'data'}]
    ) == 'DENY'


def test_nonfinal_asterisk_literal():
    """Non-final * in patterns is literal, not wildcard."""
    # Exact match with literal *
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:*Object', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:*Object', 'resource': 'bucket/key'}]
    ) == 'ALLOW'
    
    # No match (literal * doesn't match)
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/key'},
        [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:*Object', 'resource': 'bucket/key'}]
    ) == 'DENY'


def test_principal_not_pattern():
    """Principal like user:al* is literal, not a pattern."""
    assert impl.authorize(
        {'subject': 'alice', 'roles': [], 'action': 'read', 'resource': 'data'},
        [{'effect': 'ALLOW', 'principal': 'user:al*', 'action': 'read', 'resource': 'data'}]
    ) == 'DENY'


def test_no_mutation():
    """Request and policies not mutated."""
    request = {'subject': 'alice', 'roles': ['analyst'], 'action': 'read', 'resource': 'data'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'read', 'resource': 'data'}]
    request_before = str(request)
    policies_before = str(policies)
    
    impl.authorize(request, policies)
    
    assert str(request) == request_before
    assert str(policies) == policies_before
