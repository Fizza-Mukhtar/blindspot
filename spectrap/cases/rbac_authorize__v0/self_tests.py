import copy
import pytest
import impl


def make_request(subject="alice", roles=None, action="s3:GetObject", resource="docs/reports/q1.pdf"):
    if roles is None:
        roles = ["dev"]
    return {"subject": subject, "roles": roles, "action": action, "resource": resource}


def make_policy(effect="ALLOW", principal="*", action="*", resource="*"):
    return {"effect": effect, "principal": principal, "action": action, "resource": resource}


def test_simple_allow_via_role_and_wildcards():
    request = make_request(subject="alice", roles=["dev", "oncall"],
                            action="s3:GetObject", resource="docs/reports/q1.pdf")
    policies = [make_policy(effect="ALLOW", principal="role:dev",
                             action="s3:Get*", resource="docs/reports/*")]
    assert impl.authorize(request, policies) == "ALLOW"


def test_default_deny_with_empty_policies():
    request = make_request()
    assert impl.authorize(request, []) == "DENY"


def test_default_deny_when_nothing_matches():
    request = make_request(action="s3:PutObject", resource="docs/reports/q1.pdf")
    policies = [make_policy(effect="ALLOW", principal="*",
                             action="s3:GetObject", resource="docs/reports/q1.pdf")]
    assert impl.authorize(request, policies) == "DENY"


def test_deny_overrides_regardless_of_order_and_specificity():
    request = {"subject": "alice", "roles": ["contractor"],
               "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    deny_policy = {"effect": "DENY", "principal": "role:contractor",
                   "action": "*", "resource": "docs/reports/*"}
    allow_policy = {"effect": "ALLOW", "principal": "user:alice",
                    "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    assert impl.authorize(request, [deny_policy, allow_policy]) == "DENY"
    assert impl.authorize(request, [allow_policy, deny_policy]) == "DENY"


def test_principal_literal_does_not_support_glob():
    request = make_request(subject="alice", roles=[])
    policies = [make_policy(effect="ALLOW", principal="user:al*")]
    assert impl.authorize(request, policies) == "DENY"


def test_principal_wildcard_star_matches_any():
    request = make_request(subject="bob", roles=[])
    policies = [make_policy(effect="ALLOW", principal="*")]
    assert impl.authorize(request, policies) == "ALLOW"


def test_principal_role_requires_membership_in_roles_list():
    request = make_request(subject="carol", roles=["intern"])
    policies = [make_policy(effect="ALLOW", principal="role:dev")]
    assert impl.authorize(request, policies) == "DENY"


def test_empty_roles_list_is_valid_and_role_principal_never_matches():
    request = make_request(subject="dana", roles=[])
    policies = [make_policy(effect="ALLOW", principal="role:dev")]
    assert impl.authorize(request, policies) == "DENY"


def test_trailing_star_matches_prefix_including_bare_prefix():
    policies = [make_policy(effect="ALLOW", principal="*", action="s3:Get*", resource="*")]
    req_full = make_request(action="s3:GetObject")
    req_bare = make_request(action="s3:Get")
    req_other = make_request(action="s3:GetBucket")
    assert impl.authorize(req_full, policies) == "ALLOW"
    assert impl.authorize(req_bare, policies) == "ALLOW"
    assert impl.authorize(req_other, policies) == "ALLOW"


def test_resource_wildcard_requires_actual_prefix_no_extra_semantics():
    policies = [make_policy(effect="ALLOW", principal="*", action="*", resource="docs/reports/*")]
    matching = make_request(resource="docs/reports/q1.pdf")
    non_matching = make_request(resource="docs/reportsQ1")
    assert impl.authorize(matching, policies) == "ALLOW"
    assert impl.authorize(non_matching, policies) == "DENY"


def test_asterisk_not_at_end_is_literal():
    policies = [make_policy(effect="ALLOW", principal="*", action="s3:*Object", resource="*")]
    real_action_request = make_request(action="s3:GetObject")
    literal_action_request = make_request(action="s3:*Object")
    assert impl.authorize(real_action_request, policies) == "DENY"
    assert impl.authorize(literal_action_request, policies) == "ALLOW"


def test_matching_is_case_sensitive():
    request = make_request(action="s3:GetObject")
    policies = [make_policy(effect="ALLOW", principal="*", action="S3:GetObject", resource="*")]
    assert impl.authorize(request, policies) == "DENY"


def test_missing_request_field_raises_value_error():
    request = {"subject": "alice", "roles": ["dev"], "action": "s3:GetObject"}
    with pytest.raises(ValueError):
        impl.authorize(request, [])


def test_roles_not_a_list_raises_value_error():
    request = make_request(roles="dev")
    with pytest.raises(ValueError):
        impl.authorize(request, [])


def test_missing_policy_field_raises_value_error():
    request = make_request()
    bad_policy = {"effect": "ALLOW", "principal": "*", "action": "*"}
    with pytest.raises(ValueError):
        impl.authorize(request, [bad_policy])


def test_invalid_effect_raises_with_offending_value_in_message():
    request = make_request()
    bad_policy = make_policy(effect="PERMIT")
    with pytest.raises(ValueError) as excinfo:
        impl.authorize(request, [bad_policy])
    assert "PERMIT" in str(excinfo.value)


def test_lowercase_effect_is_invalid():
    request = make_request()
    bad_policy = make_policy(effect="allow")
    with pytest.raises(ValueError) as excinfo:
        impl.authorize(request, [bad_policy])
    assert "allow" in str(excinfo.value)


def test_validation_runs_before_decision_even_if_earlier_policy_settles_it():
    request = make_request(action="s3:GetObject", resource="docs/reports/q1.pdf")
    deny_policy = make_policy(effect="DENY", principal="*", action="*", resource="*")
    non_matching_bad_policy = {"effect": "BOGUS", "principal": "role:nonexistent",
                               "action": "nope", "resource": "nope"}
    with pytest.raises(ValueError):
        impl.authorize(request, [deny_policy, non_matching_bad_policy])


def test_authorize_does_not_mutate_arguments():
    request = make_request()
    policies = [make_policy(effect="ALLOW", principal="role:dev")]
    request_copy = copy.deepcopy(request)
    policies_copy = copy.deepcopy(policies)
    impl.authorize(request, policies)
    assert request == request_copy
    assert policies == policies_copy


def test_returns_only_allow_or_deny_strings():
    request = make_request()
    result_allow = impl.authorize(request, [make_policy(effect="ALLOW", principal="role:dev")])
    result_deny = impl.authorize(request, [make_policy(effect="DENY", principal="role:dev")])
    assert result_allow == "ALLOW"
    assert result_deny == "DENY"
    assert isinstance(result_allow, str) and isinstance(result_deny, str)
