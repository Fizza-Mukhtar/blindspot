import impl
import pytest


# Basic decisions
def test_allow_simple_user():
    """Test basic ALLOW with direct user principal."""
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
            'action': 's3:GetObject',
            'resource': 'bucket/file.txt'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_deny_simple_user():
    """Test basic DENY with direct user principal."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:DeleteObject',
        'resource': 'bucket/file.txt'
    }
    policies = [
        {
            'effect': 'DENY',
            'principal': 'user:alice',
            'action': 's3:DeleteObject',
            'resource': 'bucket/file.txt'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_allow_with_wildcard_principal():
    """Test ALLOW with wildcard principal (*) matching any subject."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'read',
        'resource': 'public'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': '*',
            'action': 'read',
            'resource': 'public'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_allow_with_role():
    """Test ALLOW when subject has a matching role."""
    request = {
        'subject': 'alice',
        'roles': ['admin', 'user'],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'role:admin',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


# Deny-overrides algorithm
def test_deny_overrides_allow_regardless_of_order():
    """DENY always wins over ALLOW regardless of policy order."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'read',
        'resource': 'file'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        },
        {
            'effect': 'DENY',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_role_deny_beats_user_allow():
    """DENY on a role overrides ALLOW on the user directly (per ticket scenario)."""
    request = {
        'subject': 'alice',
        'roles': ['contractor'],
        'action': 'read',
        'resource': 'docs/reports/Q1.pdf'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'docs/reports/*'
        },
        {
            'effect': 'DENY',
            'principal': 'role:contractor',
            'action': 'read',
            'resource': 'docs/reports/*'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


# Default deny
def test_empty_policies_defaults_to_deny():
    """Empty policies list returns DENY."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'any',
        'resource': 'any'
    }
    assert impl.authorize(request, []) == "DENY"


def test_no_matching_policies_denies():
    """When no policies match the request, default to DENY."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'read',
        'resource': 'file'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:bob',
            'action': 'read',
            'resource': 'file'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


# Pattern matching
def test_action_prefix_wildcard():
    """Action pattern with trailing * matches as prefix."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:Get*',
            'resource': 'bucket'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_resource_prefix_wildcard():
    """Resource pattern with trailing * matches as prefix."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'read',
        'resource': 'docs/reports/Q1.pdf'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'docs/reports/*'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_wildcard_action_matches_any():
    """Bare * in action pattern matches any action."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'anything',
        'resource': 'bucket'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': 'bucket'
        }
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_resource_pattern_no_match():
    """docs/reportsQ1 does not match docs/reports/* (no boundary semantics)."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'read',
        'resource': 'docs/reportsQ1'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'docs/reports/*'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_user_principal_literal_asterisk():
    """Principal user:al* is literal, not a glob pattern."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:al*',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


# Case sensitivity
def test_case_sensitive_action():
    """Action matching is case-sensitive."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 's3:GetObject',
        'resource': 'bucket'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:getobject',
            'resource': 'bucket'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_case_sensitive_subject():
    """Subject matching in principal is case-sensitive."""
    request = {
        'subject': 'Alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_case_sensitive_role():
    """Role name matching is case-sensitive."""
    request = {
        'subject': 'alice',
        'roles': ['Admin'],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'ALLOW',
            'principal': 'role:admin',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    assert impl.authorize(request, policies) == "DENY"


# Validation errors
def test_missing_subject_field():
    """Request missing subject field raises ValueError."""
    request = {'roles': [], 'action': 'action', 'resource': 'resource'}
    with pytest.raises(ValueError, match="subject"):
        impl.authorize(request, [])


def test_roles_not_a_list():
    """Request with roles as non-list raises ValueError."""
    request = {
        'subject': 'alice',
        'roles': 'admin',
        'action': 'action',
        'resource': 'resource'
    }
    with pytest.raises(ValueError, match="list"):
        impl.authorize(request, [])


def test_missing_policy_effect():
    """Policy missing effect field raises ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {'principal': '*', 'action': 'action', 'resource': 'resource'}
    ]
    with pytest.raises(ValueError, match="effect"):
        impl.authorize(request, policies)


def test_invalid_effect_capitalized():
    """Policy with invalid effect capitalization raises ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'Allow',
            'principal': '*',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    with pytest.raises(ValueError, match="Allow"):
        impl.authorize(request, policies)


def test_invalid_effect_typo():
    """Policy with effect typo (PERMIT) raises ValueError."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'PERMIT',
            'principal': '*',
            'action': 'action',
            'resource': 'resource'
        }
    ]
    with pytest.raises(ValueError, match="PERMIT"):
        impl.authorize(request, policies)


def test_validation_before_decision():
    """Invalid policy validated even if it wouldn't match the request."""
    request = {
        'subject': 'alice',
        'roles': [],
        'action': 'action',
        'resource': 'resource'
    }
    policies = [
        {
            'effect': 'INVALID',
            'principal': 'user:bob',
            'action': 'other',
            'resource': 'other'
        }
    ]
    with pytest.raises(ValueError, match="INVALID"):
        impl.authorize(request, policies)
