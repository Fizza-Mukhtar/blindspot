import impl
import pytest


def test_authorize_allow():
    """Matching ALLOW policy returns ALLOW"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'ALLOW'


def test_authorize_deny():
    """Matching DENY policy returns DENY"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'DENY', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'DENY'


def test_authorize_default_deny():
    """No matching policies defaults to DENY"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:bob', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'DENY'


def test_authorize_deny_overrides_allow():
    """DENY overrides ALLOW regardless of order"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'},
        {'effect': 'DENY', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'}
    ]
    assert impl.authorize(request, policies) == 'DENY'


def test_principal_wildcard():
    """Principal '*' matches any subject"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': '*', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'ALLOW'


def test_principal_user_exact_match():
    """Principal 'user:X' matches exact subject"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'ALLOW'


def test_principal_role_match():
    """Principal 'role:X' matches when X in roles"""
    request = {'subject': 'alice', 'roles': ['admin', 'contractor'], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'role:admin', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'ALLOW'


def test_principal_literal_not_wildcard():
    """Principal 'user:al*' is literal, does not match 'alice'"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:al*', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request, policies) == 'DENY'


def test_action_prefix_wildcard():
    """Action 's3:Get*' matches 's3:GetObject' and 's3:Get'"""
    request1 = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    request2 = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get*', 'resource': 'bucket/file'}]
    assert impl.authorize(request1, policies) == 'ALLOW'
    assert impl.authorize(request2, policies) == 'ALLOW'


def test_resource_prefix_wildcard():
    """Resource 'docs/reports/*' matches prefix but not partial"""
    request1 = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'docs/reports/report1'}
    request2 = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'docs/reportsQ1'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'docs/reports/*'}]
    assert impl.authorize(request1, policies) == 'ALLOW'
    assert impl.authorize(request2, policies) == 'DENY'


def test_nonfinal_wildcard_is_literal():
    """Non-final '*' is literal: 's3:*Object' matches exactly"""
    request1 = {'subject': 'alice', 'roles': [], 'action': 's3:*Object', 'resource': 'bucket/file'}
    request2 = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:*Object', 'resource': 'bucket/file'}]
    assert impl.authorize(request1, policies) == 'ALLOW'
    assert impl.authorize(request2, policies) == 'DENY'


def test_case_sensitive_matching():
    """Matching is case-sensitive"""
    request1 = {'subject': 'alice', 'roles': [], 'action': 's3:getobject', 'resource': 'bucket/file'}
    request2 = {'subject': 'alice', 'roles': [], 'action': 's3:GetObject', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:GetObject', 'resource': 'bucket/file'}]
    assert impl.authorize(request1, policies) == 'DENY'
    assert impl.authorize(request2, policies) == 'ALLOW'


def test_request_missing_field():
    """Missing request field raises ValueError"""
    request = {'subject': 'alice', 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    with pytest.raises(ValueError, match="roles"):
        impl.authorize(request, policies)


def test_request_roles_not_list():
    """Request 'roles' must be a list"""
    request = {'subject': 'alice', 'roles': 'admin', 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    with pytest.raises(ValueError, match="list"):
        impl.authorize(request, policies)


def test_policy_missing_field():
    """Missing policy field raises ValueError"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    with pytest.raises(ValueError, match="effect"):
        impl.authorize(request, policies)


def test_policy_invalid_effect():
    """Invalid policy effect raises ValueError with value in message"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'effect': 'Allow', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    with pytest.raises(ValueError, match="Allow"):
        impl.authorize(request, policies)


def test_validation_before_decision():
    """All validation happens before any decision"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'},
        {'effect': 'Invalid', 'principal': 'user:bob', 'action': 's3:Get', 'resource': 'bucket/file'}
    ]
    with pytest.raises(ValueError):
        impl.authorize(request, policies)


def test_request_not_mutated():
    """Request dict is not mutated"""
    request = {'subject': 'alice', 'roles': ['admin'], 'action': 's3:Get', 'resource': 'bucket/file'}
    request_copy = dict(request)
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    impl.authorize(request, policies)
    assert request == request_copy


def test_policies_not_mutated():
    """Policies list is not mutated"""
    request = {'subject': 'alice', 'roles': [], 'action': 's3:Get', 'resource': 'bucket/file'}
    policies = [{'effect': 'ALLOW', 'principal': 'user:alice', 'action': 's3:Get', 'resource': 'bucket/file'}]
    policies_copy = [dict(p) for p in policies]
    impl.authorize(request, policies)
    assert policies == policies_copy


def test_contractor_scenario():
    """Ticket scenario: role DENY overrides user ALLOW"""
    request = {'subject': 'alice', 'roles': ['contractor'], 'action': 'docs:Read', 'resource': 'docs/reports/Q1'}
    policies = [
        {'effect': 'ALLOW', 'principal': 'user:alice', 'action': 'docs:Read', 'resource': 'docs/reports/*'},
        {'effect': 'DENY', 'principal': 'role:contractor', 'action': 'docs:Read', 'resource': 'docs/reports/*'}
    ]
    assert impl.authorize(request, policies) == 'DENY'
