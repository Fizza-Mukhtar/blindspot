import pytest
import impl


def test_ticket_example():
    """Example from ticket: €10.00 split 3 ways."""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]
    assert sum(result) == 10


def test_two_payees_equal_weights():
    """Split evenly between two equal-weight payees."""
    result = impl.allocate(10, [1, 1])
    assert result == [5, 5]
    assert sum(result) == 10


def test_three_payees_equal_weights():
    """Split among three equal-weight payees with tie-breaking."""
    result = impl.allocate(10, [1, 1, 1])
    assert result == [4, 3, 3]
    assert sum(result) == 10


def test_single_payee():
    """Allocate to a single payee."""
    result = impl.allocate(100, [1])
    assert result == [100]


def test_zero_total():
    """Zero total amount returns all zeros."""
    result = impl.allocate(0, [1, 2, 3])
    assert result == [0, 0, 0]


def test_zero_weight():
    """Payee with zero weight receives exactly zero."""
    result = impl.allocate(10, [0, 1, 2])
    assert sum(result) == 10
    assert result[0] == 0


def test_negative_total_basic():
    """Negative total with basic split."""
    result = impl.allocate(-10, [1, 2, 4])
    assert sum(result) == -10
    assert result == [-1, -3, -6]


def test_negative_total_uneven():
    """Negative total with uneven split shows correct tie-breaking."""
    result = impl.allocate(-5, [1, 1])
    assert sum(result) == -5
    assert result == [-3, -2]


def test_negative_symmetry():
    """allocate(-t, w) negates allocate(t, w)."""
    test_cases = [
        (10, [1, 2, 4]),
        (5, [1, 1]),
        (100, [1, 2, 3]),
    ]
    for total, weights in test_cases:
        pos_result = impl.allocate(total, weights)
        neg_result = impl.allocate(-total, weights)
        assert neg_result == [-x for x in pos_result]


def test_sum_invariant():
    """Sum of allocation always equals total_cents."""
    test_cases = [
        (10, [1, 2, 4]),
        (100, [3, 7]),
        (1, [1, 1, 1]),
        (13, [1, 1, 1, 1]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total


def test_length_invariant():
    """Result length equals weights length."""
    test_cases = [
        (10, [1]),
        (10, [1, 2]),
        (10, [1, 2, 3, 4, 5]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert len(result) == len(weights)


def test_no_input_mutation():
    """Input list is not mutated."""
    weights = [1, 2, 3]
    weights_copy = weights.copy()
    impl.allocate(10, weights)
    assert weights == weights_copy


def test_empty_weights_error():
    """Empty weights list raises ValueError."""
    with pytest.raises(ValueError, match="weights is empty"):
        impl.allocate(10, [])


def test_negative_weight_error():
    """Negative weight raises ValueError."""
    with pytest.raises(ValueError, match="weights contains negative values"):
        impl.allocate(10, [1, -2, 3])


def test_all_zero_weights_error():
    """All zero weights raises ValueError."""
    with pytest.raises(ValueError, match="weights are all zero"):
        impl.allocate(10, [0, 0, 0])


def test_validation_with_zero_total():
    """Error validation happens even with zero total."""
    with pytest.raises(ValueError, match="weights are all zero"):
        impl.allocate(0, [0, 0])


def test_large_numbers():
    """Large total and weights work correctly."""
    result = impl.allocate(1_000_000, [1, 1, 1])
    assert sum(result) == 1_000_000
    assert len(result) == 3
