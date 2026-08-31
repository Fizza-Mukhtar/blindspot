"""Authoritative examples for IAM-2287.

Every assertion here is taken from the cited standard or from an explicit
sentence of SPEC.md, not from the reference implementation's behaviour.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.

Source: XACML 3.0 core specification, deny-overrides rule-combining algorithm
(Appendix C.2) --
https://docs.oasis-open.org/xacml/3.0/xacml-3.0-core-spec-os-en.html
"""

import pytest

import impl

REQ = {
    "subject": "alice",
    "roles": ["contractor"],
    "action": "s3:GetObject",
    "resource": "docs/reports/q1.pdf",
}


def req(**overrides):
    merged = dict(REQ)
    merged.update(overrides)
    return merged


def policy(effect, principal, action, resource):
    return {
        "effect": effect,
        "principal": principal,
        "action": action,
        "resource": resource,
    }


ALLOW_EXACT = policy("ALLOW", "user:alice", "s3:GetObject", "docs/reports/q1.pdf")
DENY_ROLE = policy("DENY", "role:contractor", "*", "docs/reports/*")


def test_deny_wins_when_the_deny_is_listed_after_the_allow():
    """Deny-overrides, C.2: a matching DENY decides, whatever else matched."""
    assert impl.authorize(req(), [ALLOW_EXACT, DENY_ROLE]) == "DENY"


def test_deny_wins_when_the_deny_is_listed_before_the_allow():
    """Deny-overrides is order-independent: SPEC.md 'regardless of the order'."""
    assert impl.authorize(req(), [DENY_ROLE, ALLOW_EXACT]) == "DENY"


def test_role_level_deny_beats_user_level_allow():
    """SPEC.md: 'regardless of how specific the principal is'."""
    decision = impl.authorize(
        req(), [policy("ALLOW", "user:alice", "*", "*"), policy("DENY", "role:contractor", "*", "*")]
    )
    assert decision == "DENY"


def test_broad_deny_beats_exact_allow():
    """SPEC.md: 'regardless of how specific' the action/resource patterns are."""
    assert impl.authorize(req(), [ALLOW_EXACT, policy("DENY", "*", "*", "*")]) == "DENY"


def test_single_matching_allow_is_allowed():
    """Deny-overrides rule 2: at least one ALLOW and no DENY -> Permit."""
    assert impl.authorize(req(), [ALLOW_EXACT]) == "ALLOW"


def test_default_deny_when_nothing_matches():
    """SPEC.md rule 3: a request no policy speaks to is refused."""
    policies = [policy("ALLOW", "user:bob", "*", "*"), policy("ALLOW", "*", "s3:Put*", "*")]
    assert impl.authorize(req(), policies) == "DENY"


def test_empty_policy_list_is_denied():
    """SPEC.md rule 3: the empty list is the degenerate default-deny case."""
    assert impl.authorize(req(), []) == "DENY"


def test_non_matching_deny_is_ignored():
    """A DENY only overrides if it matches; C.2 combines applicable rules only."""
    policies = [
        policy("ALLOW", "role:dev", "s3:Get*", "docs/*"),
        policy("DENY", "role:contractor", "*", "*"),
    ]
    assert impl.authorize(req(roles=["dev"]), policies) == "ALLOW"


def test_wildcard_principal_matches_any_subject():
    """SPEC.md: principal '*' means any principal."""
    assert impl.authorize(req(subject="zed", roles=[]), [policy("ALLOW", "*", "*", "*")]) == "ALLOW"


def test_role_principal_matches_any_role_in_the_list():
    """SPEC.md: 'role:' followed by one of the roles in the request's list."""
    request = req(roles=["dev", "oncall"])
    assert impl.authorize(request, [policy("ALLOW", "role:oncall", "*", "*")]) == "ALLOW"


def test_principal_is_not_a_pattern():
    """SPEC.md: 'user:al*' is the literal principal named al*, not a prefix."""
    assert impl.authorize(req(), [policy("ALLOW", "user:al*", "*", "*")]) == "DENY"


def test_trailing_star_matches_the_bare_prefix_itself():
    """SPEC.md: 's3:Get*' matches 's3:GetObject' and 'also the bare s3:Get'."""
    assert impl.authorize(req(action="s3:Get"), [policy("ALLOW", "*", "s3:Get*", "*")]) == "ALLOW"


def test_trailing_star_is_a_prefix_match_not_a_path_segment_match():
    """SPEC.md: 'docs/reports/*' does not match 'docs/reportsQ1'."""
    pol = [policy("ALLOW", "*", "*", "docs/reports/*")]
    assert impl.authorize(req(resource="docs/reportsQ1"), pol) == "DENY"
    assert impl.authorize(req(resource="docs/reports/q1.pdf"), pol) == "ALLOW"


def test_bare_star_pattern_matches_everything():
    """SPEC.md: 'The pattern * on its own therefore matches everything.'"""
    request = req(action="anything:at-all", resource="somewhere/else")
    assert impl.authorize(request, [policy("ALLOW", "*", "*", "*")]) == "ALLOW"


def test_interior_star_is_a_literal_asterisk():
    """SPEC.md: 's3:*Object' matches only the action literally named that."""
    pol = [policy("ALLOW", "*", "s3:*Object", "*")]
    assert impl.authorize(req(action="s3:GetObject"), pol) == "DENY"
    assert impl.authorize(req(action="s3:*Object"), pol) == "ALLOW"


def test_matching_is_case_sensitive():
    """SPEC.md: 'S3:GetObject and s3:GetObject are different actions.'"""
    assert impl.authorize(req(), [policy("ALLOW", "*", "S3:Get*", "*")]) == "DENY"
    assert impl.authorize(req(), [policy("ALLOW", "*", "*", "DOCS/*")]) == "DENY"


@pytest.mark.parametrize("bad", ["Allow", "allow", "deny", "PERMIT", "", "NEUTRAL"])
def test_unknown_effect_raises_value_error_naming_the_value(bad):
    """SPEC.md errors: effect must be exactly 'ALLOW' or exactly 'DENY'."""
    with pytest.raises(ValueError) as excinfo:
        impl.authorize(req(), [policy(bad, "*", "*", "*")])
    assert bad in str(excinfo.value)


def test_validation_precedes_evaluation():
    """SPEC.md: 'Validate everything before deciding anything.'"""
    policies = [policy("DENY", "*", "*", "*"), policy("PERMIT", "user:bob", "x", "y")]
    with pytest.raises(ValueError):
        impl.authorize(req(), policies)


@pytest.mark.parametrize("missing", ["effect", "principal", "action", "resource"])
def test_policy_missing_a_required_field_raises_value_error(missing):
    """SPEC.md errors: every policy carries all four fields."""
    broken = policy("ALLOW", "*", "*", "*")
    del broken[missing]
    with pytest.raises(ValueError):
        impl.authorize(req(), [broken])


@pytest.mark.parametrize("missing", ["subject", "roles", "action", "resource"])
def test_request_missing_a_required_field_raises_value_error(missing):
    """SPEC.md errors: the request carries all four fields."""
    broken = req()
    del broken[missing]
    with pytest.raises(ValueError):
        impl.authorize(broken, [])


def test_roles_must_be_a_list():
    """SPEC.md errors: 'or if roles is not a list, raise ValueError'."""
    with pytest.raises(ValueError):
        impl.authorize(req(roles="contractor"), [])


def test_arguments_are_not_mutated():
    """SPEC.md: 'It does not mutate either argument.'"""
    request = req()
    policies = [ALLOW_EXACT, DENY_ROLE]
    snapshot_request = dict(request)
    snapshot_policies = [dict(p) for p in policies]
    impl.authorize(request, policies)
    assert request == snapshot_request
    assert policies == snapshot_policies
