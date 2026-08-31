import pytest
import impl


def test_allow_matches():
    """Request matching ALLOW policy returns ALLOW."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "user:alice", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_deny_matches():
    """Request matching DENY policy returns DENY."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "DENY", "principal": "user:alice", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "DENY"


def test_no_match_defaults_deny():
    """Request with no matching policy defaults to DENY."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "user:bob", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "DENY"


def test_deny_overrides_allow():
    """DENY policy overrides ALLOW policy regardless of order."""
    request = {"subject": "alice", "roles": ["contractor"], "action": "read", "resource": "docs/reports/file.txt"}
    policies = [
        {"effect": "ALLOW", "principal": "user:alice", "action": "*", "resource": "*"},
        {"effect": "DENY", "principal": "role:contractor", "action": "*", "resource": "docs/reports/*"}
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_principal_wildcard():
    """Principal '*' matches any principal."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_principal_user():
    """Principal 'user:X' matches request with subject X."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "user:alice", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_principal_role():
    """Principal 'role:X' matches when X is in request roles."""
    request = {"subject": "alice", "roles": ["admin"], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "role:admin", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_principal_literal_not_wildcard():
    """Principal 'user:al*' is literal, not a pattern."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "user:al*", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "DENY"


def test_action_exact_match():
    """Action matches when equal."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_action_wildcard():
    """Action '*' matches any action."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "*", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_action_prefix_match():
    """Action 's3:Get*' matches 's3:GetObject'."""
    request = {"subject": "alice", "roles": [], "action": "s3:GetObject", "resource": "bucket"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "s3:Get*", "resource": "bucket"}]
    assert impl.authorize(request, policies) == "ALLOW"


def test_action_literal_star_in_middle():
    """Action with non-final * is literal: 's3:*Object' only matches that action."""
    request = {"subject": "alice", "roles": [], "action": "s3:GetObject", "resource": "bucket"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "s3:*Object", "resource": "bucket"}]
    assert impl.authorize(request, policies) == "DENY"


def test_resource_prefix_does_not_overmatch():
    """Resource 'docs/reports/*' does not match 'docs/reportsQ1'."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "docs/reportsQ1"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "read", "resource": "docs/reports/*"}]
    assert impl.authorize(request, policies) == "DENY"


def test_request_validation():
    """Raises ValueError for invalid request."""
    request = {"subject": "alice", "roles": "admin", "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "*", "action": "read", "resource": "file.txt"}]
    with pytest.raises(ValueError, match="list"):
        impl.authorize(request, policies)


def test_policy_validation():
    """Raises ValueError for invalid policy effect."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "INVALID", "principal": "*", "action": "read", "resource": "file.txt"}]
    with pytest.raises(ValueError, match="INVALID"):
        impl.authorize(request, policies)


def test_validation_before_decision():
    """Validate all policies before making decision."""
    request = {"subject": "alice", "roles": [], "action": "read", "resource": "file.txt"}
    policies = [
        {"effect": "ALLOW", "principal": "*", "action": "read", "resource": "file.txt"},
        {"effect": "INVALID", "principal": "*", "action": "read", "resource": "file.txt"}
    ]
    with pytest.raises(ValueError):
        impl.authorize(request, policies)


def test_case_sensitive():
    """Subject and action matching is case-sensitive."""
    request = {"subject": "alice", "roles": [], "action": "Read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "user:Alice", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "DENY"


def test_multiple_roles():
    """Request with multiple roles matches any matching role principal."""
    request = {"subject": "alice", "roles": ["user", "admin"], "action": "read", "resource": "file.txt"}
    policies = [{"effect": "ALLOW", "principal": "role:admin", "action": "read", "resource": "file.txt"}]
    assert impl.authorize(request, policies) == "ALLOW"
