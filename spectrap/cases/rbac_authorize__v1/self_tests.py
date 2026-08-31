import pytest

import impl


def make_request(subject="alice", roles=None, action="s3:GetObject", resource="docs/reports/q1.pdf"):
    if roles is None:
        roles = ["dev"]
    return {"subject": subject, "roles": roles, "action": action, "resource": resource}


def test_worked_example_deny_overrides_allow():
    request = {"subject": "alice", "roles": ["contractor"],
               "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    policies = [
        {"effect": "DENY", "principal": "role:contractor",
         "action": "*", "resource": "docs/reports/*"},
        {"effect": "ALLOW", "principal": "user:alice",
         "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_worked_example_order_reversed_still_deny():
    request = {"subject": "alice", "roles": ["contractor"],
               "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    policies = [
        {"effect": "ALLOW", "principal": "user:alice",
         "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
        {"effect": "DENY", "principal": "role:contractor",
         "action": "*", "resource": "docs/reports/*"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_simple_allow_match():
    request = make_request(roles=["dev"])
    policies = [
        {"effect": "ALLOW", "principal": "role:dev",
         "action": "s3:Get*", "resource": "docs/reports/*"},
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_empty_policies_defaults_to_deny():
    request = make_request()
    assert impl.authorize(request, []) == "DENY"


def test_no_matching_policy_defaults_to_deny():
    request = make_request(action="s3:PutObject")
    policies = [
        {"effect": "ALLOW", "principal": "role:dev",
         "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_principal_literal_asterisk_not_prefix_match():
    # "user:al*" is literal; does not match subject "alice"
    request = make_request(subject="alice", roles=[])
    policies = [
        {"effect": "ALLOW", "principal": "user:al*",
         "action": "*", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_principal_wildcard_star_matches_any():
    request = make_request(subject="bob", roles=[])
    policies = [
        {"effect": "ALLOW", "principal": "*",
         "action": "*", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_action_pattern_bare_prefix_matches_exact_prefix_value():
    # "s3:Get*" matches the bare "s3:Get" itself
    request = make_request(action="s3:Get", resource="anything")
    policies = [
        {"effect": "ALLOW", "principal": "*",
         "action": "s3:Get*", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "ALLOW"


def test_resource_pattern_no_slash_no_match():
    # "docs/reports/*" does not match "docs/reportsQ1" (no slash boundary)
    request = make_request(resource="docs/reportsQ1")
    policies = [
        {"effect": "ALLOW", "principal": "*",
         "action": "*", "resource": "docs/reports/*"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_asterisk_not_at_end_is_literal():
    # "s3:*Object" is literal, does not match "s3:GetObject"
    request = make_request(action="s3:GetObject")
    policies = [
        {"effect": "ALLOW", "principal": "*",
         "action": "s3:*Object", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "DENY"

    request2 = make_request(action="s3:*Object")
    policies2 = [
        {"effect": "ALLOW", "principal": "*",
         "action": "s3:*Object", "resource": "*"},
    ]
    assert impl.authorize(request2, policies2) == "ALLOW"


def test_case_sensitive_matching():
    request = make_request(action="S3:GetObject")
    policies = [
        {"effect": "ALLOW", "principal": "*",
         "action": "s3:GetObject", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_empty_roles_list_allowed_and_no_role_match():
    request = make_request(roles=[])
    policies = [
        {"effect": "ALLOW", "principal": "role:dev",
         "action": "*", "resource": "*"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_deny_beats_allow_regardless_of_specificity_and_principal_type():
    request = {"subject": "alice", "roles": ["contractor", "dev"],
               "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    policies = [
        {"effect": "DENY", "principal": "*",
         "action": "*", "resource": "*"},
        {"effect": "ALLOW", "principal": "user:alice",
         "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"},
    ]
    assert impl.authorize(request, policies) == "DENY"


def test_request_missing_field_raises_value_error():
    request = {"subject": "alice", "roles": ["dev"], "action": "s3:GetObject"}
    with pytest.raises(ValueError):
        impl.authorize(request, [])


def test_request_roles_not_a_list_raises_value_error():
    request = {"subject": "alice", "roles": "dev",
               "action": "s3:GetObject", "resource": "docs/reports/q1.pdf"}
    with pytest.raises(ValueError):
        impl.authorize(request, [])


def test_policy_missing_field_raises_value_error():
    request = make_request()
    policies = [
        {"effect": "ALLOW", "principal": "*", "action": "*"},
    ]
    with pytest.raises(ValueError):
        impl.authorize(request, policies)


def test_policy_invalid_effect_message_contains_value():
    request = make_request()
    policies = [
        {"effect": "PERMIT", "principal": "*", "action": "*", "resource": "*"},
    ]
    with pytest.raises(ValueError, match="PERMIT"):
        impl.authorize(request, policies)


def test_validation_happens_before_short_circuit_deny():
    # An earlier DENY that would settle the outcome must not skip validation
    # of a later malformed policy.
    request = make_request()
    policies = [
        {"effect": "DENY", "principal": "*", "action": "*", "resource": "*"},
        {"effect": "allow", "principal": "*", "action": "*", "resource": "*"},
    ]
    with pytest.raises(ValueError, match="allow"):
        impl.authorize(request, policies)


def test_does_not_mutate_arguments():
    request = make_request()
    policies = [
        {"effect": "ALLOW", "principal": "role:dev",
         "action": "s3:Get*", "resource": "docs/reports/*"},
    ]
    request_copy = dict(request)
    policies_copy = [dict(p) for p in policies]
    impl.authorize(request, policies)
    assert request == request_copy
    assert policies == policies_copy
