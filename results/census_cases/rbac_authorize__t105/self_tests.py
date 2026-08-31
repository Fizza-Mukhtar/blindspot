import impl
import pytest


class TestBasicDecisions:
    """Test basic ALLOW and DENY decisions."""

    def test_single_allow_policy(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 's3:GetObject',
            'resource': 'bucket/file.txt'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:GetObject',
            'resource': 'bucket/file.txt'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_single_deny_policy(self):
        request = {
            'subject': 'bob',
            'roles': [],
            'action': 's3:DeleteObject',
            'resource': 'bucket/file.txt'
        }
        policies = [{
            'effect': 'DENY',
            'principal': 'user:bob',
            'action': 's3:DeleteObject',
            'resource': 'bucket/file.txt'
        }]
        assert impl.authorize(request, policies) == "DENY"

    def test_empty_policies_defaults_to_deny(self):
        request = {
            'subject': 'charlie',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        assert impl.authorize(request, []) == "DENY"

    def test_no_matching_policy_defaults_to_deny(self):
        request = {
            'subject': 'david',
            'roles': [],
            'action': 'write',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:eve',
            'action': 'write',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "DENY"


class TestPrincipalMatching:
    """Test principal matching logic."""

    def test_wildcard_principal(self):
        request = {
            'subject': 'anyone',
            'roles': [],
            'action': 'read',
            'resource': 'public'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': '*',
            'action': 'read',
            'resource': 'public'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_user_principal_exact_match(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_role_principal_match(self):
        request = {
            'subject': 'alice',
            'roles': ['admin', 'editor'],
            'action': 'write',
            'resource': 'document'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'role:admin',
            'action': 'write',
            'resource': 'document'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_principal_with_wildcard_not_pattern(self):
        # "user:al*" should match literally, not as a pattern
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:al*',
            'action': 'read',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "DENY"


class TestPatternMatching:
    """Test action and resource pattern matching."""

    def test_action_wildcard_matches_all(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'anything',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': '*',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_action_prefix_matching(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 's3:GetObject',
            'resource': 'bucket'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:Get*',
            'resource': 'bucket'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_resource_prefix_matching(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'docs/reports/Q1'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'docs/reports/*'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_resource_prefix_not_reaching_different_path(self):
        # docs/reports/* should not match docs/reportsQ1
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'docs/reportsQ1'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'docs/reports/*'
        }]
        assert impl.authorize(request, policies) == "DENY"

    def test_pattern_with_non_final_asterisk_literal(self):
        # "s3:*Object" should match only the literal action "s3:*Object"
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 's3:GetObject',
            'resource': 'bucket'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:*Object',
            'resource': 'bucket'
        }]
        assert impl.authorize(request, policies) == "DENY"


class TestDenyOverrides:
    """Test deny-overrides logic (XACML)."""

    def test_deny_overrides_allow_regardless_of_position(self):
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

    def test_deny_on_role_beats_allow_on_user(self):
        # From ticket: contractor DENY beats alice ALLOW
        request = {
            'subject': 'alice',
            'roles': ['contractor'],
            'action': 'read',
            'resource': 'docs/reports/file.txt'
        }
        policies = [
            {
                'effect': 'ALLOW',
                'principal': 'user:alice',
                'action': 'read',
                'resource': 'docs/reports/file.txt'
            },
            {
                'effect': 'DENY',
                'principal': 'role:contractor',
                'action': 'read',
                'resource': 'docs/reports/*'
            }
        ]
        assert impl.authorize(request, policies) == "DENY"


class TestValidation:
    """Test request and policy validation."""

    def test_request_missing_subject(self):
        request = {
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        with pytest.raises(ValueError, match="subject"):
            impl.authorize(request, [])

    def test_request_missing_roles(self):
        request = {
            'subject': 'alice',
            'action': 'read',
            'resource': 'file'
        }
        with pytest.raises(ValueError, match="roles"):
            impl.authorize(request, [])

    def test_request_missing_action(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'resource': 'file'
        }
        with pytest.raises(ValueError, match="action"):
            impl.authorize(request, [])

    def test_request_missing_resource(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read'
        }
        with pytest.raises(ValueError, match="resource"):
            impl.authorize(request, [])

    def test_request_roles_not_list(self):
        request = {
            'subject': 'alice',
            'roles': 'admin',
            'action': 'read',
            'resource': 'file'
        }
        with pytest.raises(ValueError, match="roles.*list"):
            impl.authorize(request, [])

    def test_policy_missing_effect(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }]
        with pytest.raises(ValueError, match="effect"):
            impl.authorize(request, policies)

    def test_policy_invalid_effect_allow_typo(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'Allow',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }]
        with pytest.raises(ValueError, match="Allow"):
            impl.authorize(request, policies)

    def test_policy_invalid_effect_permit(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'PERMIT',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }]
        with pytest.raises(ValueError, match="PERMIT"):
            impl.authorize(request, policies)

    def test_validation_before_decision(self):
        # Validate all policies even if early ones would not match
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
            },
            {
                'effect': 'INVALID',
                'principal': 'user:alice',
                'action': 'read',
                'resource': 'file'
            }
        ]
        with pytest.raises(ValueError, match="INVALID"):
            impl.authorize(request, policies)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_case_sensitivity_in_action(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'Read',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "DENY"

    def test_no_mutation_of_request(self):
        request = {
            'subject': 'alice',
            'roles': ['admin'],
            'action': 'read',
            'resource': 'file'
        }
        request_copy = dict(request)
        request_copy['roles'] = list(request_copy['roles'])

        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 'read',
            'resource': 'file'
        }]

        impl.authorize(request, policies)
        assert request == request_copy

    def test_empty_subject(self):
        request = {
            'subject': '',
            'roles': [],
            'action': 'read',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:',
            'action': 'read',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "ALLOW"

    def test_prefix_match_at_boundary(self):
        request = {
            'subject': 'alice',
            'roles': [],
            'action': 's3:Get',
            'resource': 'file'
        }
        policies = [{
            'effect': 'ALLOW',
            'principal': 'user:alice',
            'action': 's3:Get*',
            'resource': 'file'
        }]
        assert impl.authorize(request, policies) == "ALLOW"
