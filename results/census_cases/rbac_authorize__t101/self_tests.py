import impl
import pytest


# Basic functionality
def test_empty_policies_defaults_to_deny():
    """Empty policies list should default to DENY."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    result = impl.authorize(request, [])
    assert result == "DENY"


def test_single_matching_allow_policy():
    """A single matching ALLOW policy should return ALLOW."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:*',
            'resource': 'bucket/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_single_matching_deny_policy():
    """A single matching DENY policy should return DENY."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'DENY',
            'principal': 'user:alice',
            'action': 's3:*',
            'resource': 'bucket/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_no_matching_policy_defaults_to_deny():
    """When no policy matches, should default to DENY."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:bob',
            'action': 's3:*',
            'resource': 'bucket/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


# Principal matching
def test_principal_wildcard():
    """Principal '*' should match any principal."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': '*',
            'action': 's3:*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_user_principal_exact_match():
    """'user:X' should match exact subject."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_user_principal_no_match():
    """'user:X' should not match different subject."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:bob',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_role_principal_match():
    """'role:X' should match when X is in roles."""
    request = {
        'subject': 'alice',
        'roles': ['contractor', 'viewer'],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'role:viewer',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_role_principal_no_match():
    """'role:X' should not match when X is not in roles."""
    request = {
        'subject': 'alice',
        'roles': ['viewer'],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'role:admin',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


# Action and resource pattern matching
def test_action_trailing_wildcard():
    """Action pattern 's3:Get*' should prefix match 's3:GetObject'."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:Get*',
            'resource': 'resource'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_action_non_final_wildcard_is_literal():
    """Non-final * in action is literal, not a pattern."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:*Object',
            'resource': 'resource'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_resource_prefix_matching():
    """Resource pattern matching should work like action matching."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'docs/reports/Q1.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'action',
            'resource': 'docs/reports/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_resource_does_not_match_substring():
    """Resource 'docs/reports/*' should not match 'docs/reportsQ1'."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'docs/reportsQ1'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'action',
            'resource': 'docs/reports/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


# XACML deny-overrides algorithm
def test_deny_overrides_allow():
    """DENY policy should override ALLOW policy regardless of order."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        },
        {
            'effect': 'DENY',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_contractor_deny_overrides_user_allow():
    """The ticket scenario: role DENY overrides user ALLOW."""
    request = {
        'subject': 'alice',
        'roles': ['contractor'],
        'action': 'docs:Read',
        'resource': 'docs/reports/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': 'docs/reports/*'
        },
        {
            'effect': 'DENY',
            'principal': 'role:contractor',
            'action': '*',
            'resource': 'docs/reports/*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


# Validation: request fields
def test_request_missing_subject():
    """Request missing 'subject' should raise ValueError."""
    request = {
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    with pytest.raises(ValueError, match="subject"):
        impl.authorize(request, [])


def test_request_missing_roles():
    """Request missing 'roles' should raise ValueError."""
    request = {
        'subject': 'alice',
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    with pytest.raises(ValueError, match="roles"):
        impl.authorize(request, [])


def test_request_missing_action():
    """Request missing 'action' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'resource': 'bucket/file.txt'
    }
    with pytest.raises(ValueError, match="action"):
        impl.authorize(request, [])


def test_request_missing_resource():
    """Request missing 'resource' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject'
    }
    with pytest.raises(ValueError, match="resource"):
        impl.authorize(request, [])


def test_request_roles_not_list():
    """Request 'roles' not a list should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': 'contractor',
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    with pytest.raises(ValueError, match="list"):
        impl.authorize(request, [])


# Validation: policy fields
def test_policy_missing_effect():
    """Policy missing 'effect' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError, match="effect"):
        impl.authorize(request, policies)


def test_policy_missing_principal():
    """Policy missing 'principal' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError, match="principal"):
        impl.authorize(request, policies)


def test_policy_missing_action():
    """Policy missing 'action' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError, match="action"):
        impl.authorize(request, policies)


def test_policy_missing_resource():
    """Policy missing 'resource' should raise ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*'
        }
    ]
    with pytest.raises(ValueError, match="resource"):
        impl.authorize(request, policies)


# Validation: effect values
def test_invalid_effect_allow_lowercase():
    """Effect 'Allow' (wrong case) should raise ValueError with value in message."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'Allow',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError) as exc_info:
        impl.authorize(request, policies)
    assert 'Allow' in str(exc_info.value)


def test_invalid_effect_permit():
    """Effect 'PERMIT' should raise ValueError with value in message."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'PERMIT',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError) as exc_info:
        impl.authorize(request, policies)
    assert 'PERMIT' in str(exc_info.value)


def test_invalid_effect_deny_lowercase():
    """Effect 'deny' (lowercase) should raise ValueError with value in message."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'deny',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError) as exc_info:
        impl.authorize(request, policies)
    assert 'deny' in str(exc_info.value)


# Edge cases and case sensitivity
def test_case_sensitivity_subject():
    """Principal and subject matching should be case-sensitive."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:Alice',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_case_sensitivity_action():
    """Action matching should be case-sensitive."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:getobject',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_user_principal_with_wildcard_is_literal():
    """'user:al*' is a literal principal, not a pattern."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:al*',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "DENY"


def test_multiple_policies_complex_scenario():
    """Complex scenario with multiple policies and roles."""
    request = {
        'subject': 'bob',
        'roles': ['admin', 'user'],
        'action': 's3:ListBucket',
        'resource': 's3:mybucket'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'role:user',
            'action': 's3:List*',
            'resource': 's3:*'
        },
        {
            'effect': 'DENY',
            'principal': 'role:restricted',
            'action': '*',
            'resource': '*'
        },
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        }
    ]
    result = impl.authorize(request, policies)
    assert result == "ALLOW"


def test_validation_happens_before_decision():
    """Validation errors should be raised before decision logic runs."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': '*'
        },
        {
            'effect': 'INVALID',
            'principal': 'user:bob',
            'action': '*',
            'resource': '*'
        }
    ]
    with pytest.raises(ValueError) as exc_info:
        impl.authorize(request, policies)
    assert 'INVALID' in str(exc_info.value)
