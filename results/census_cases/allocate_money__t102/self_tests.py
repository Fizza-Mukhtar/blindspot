import pytest
import impl


def test_example_from_spec():
    """Test the example from the ticket: allocate(10, [1, 2, 4]) == [1, 3, 6]"""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]
    assert sum(result) == 10


def test_single_payee():
    """Single payee gets the entire amount"""
    result = impl.allocate(100, [1])
    assert result == [100]
    assert sum(result) == 100


def test_exact_division_equal_weights():
    """When division is exact, no remainders to distribute"""
    result = impl.allocate(100, [1, 1, 1, 1])
    assert result == [25, 25, 25, 25]
    assert sum(result) == 100


def test_one_cent_split_two_payees():
    """1 cent split between two equal weights: earliest index gets it"""
    result = impl.allocate(1, [1, 1])
    assert sum(result) == 1
    assert result == [1, 0]


def test_remainder_distribution_three_payees():
    """Test remainder distribution with multiple payees"""
    result = impl.allocate(5, [1, 1, 1])
    assert sum(result) == 5
    # All have remainder 2 out of W=3, two units distributed to first two by index
    assert result == [2, 2, 1]


def test_tie_breaking_by_index():
    """When remainders tie, earliest index gets the extra unit"""
    result = impl.allocate(5, [1, 1, 1, 1])
    assert sum(result) == 5
    # All have remainder 1, first payee gets the one extra unit
    assert result == [2, 1, 1, 1]


def test_negative_amount_simple():
    """Negative amount reverses the sign of each allocation"""
    result = impl.allocate(-10, [1, 1])
    assert sum(result) == -10
    assert result == [-5, -5]


def test_negative_amount_spec_example():
    """Verify the spec's negative example: allocate(-5, [1, 1]) == [-3, -2]"""
    result = impl.allocate(-5, [1, 1])
    assert result == [-3, -2]
    assert sum(result) == -5


def test_zero_amount_returns_all_zeros():
    """Zero amount always returns all zeros"""
    result = impl.allocate(0, [1, 2, 3, 4])
    assert result == [0, 0, 0, 0]
    assert sum(result) == 0


def test_zero_weight_in_list():
    """Payee with zero weight gets exactly zero"""
    result = impl.allocate(100, [1, 0, 2])
    assert sum(result) == 100
    assert result[1] == 0  # Zero weight payee
    assert result[0] + result[2] == 100


def test_multiple_zero_weights():
    """Multiple zero weights all get zero"""
    result = impl.allocate(100, [2, 0, 3, 0])
    assert result == [40, 0, 60, 0]
    assert sum(result) == 100


def test_large_amount():
    """Large amount allocation maintains precision"""
    result = impl.allocate(1000000, [1, 2, 3])
    assert sum(result) == 1000000
    # W=6: floors are [166666, 333333, 500000], leftover=1 goes to payee 0 (remainder 4)
    assert result == [166667, 333333, 500000]


def test_sum_invariant_various_amounts():
    """Critical: sum(result) == total_cents must always hold"""
    test_cases = [
        (1, [1, 1, 1]),
        (10, [1, 2, 3, 4]),
        (999, [7, 11, 13]),
        (-50, [1, 1, 1, 1, 1]),
        (-999, [2, 5, 7]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total, f"Failed for allocate({total}, {weights})"


def test_no_mutation_of_input():
    """Weights list is not mutated"""
    weights = [1, 2, 3]
    original = weights.copy()
    impl.allocate(10, weights)
    assert weights == original


def test_error_empty_weights():
    """Empty weights list raises ValueError"""
    with pytest.raises(ValueError, match="empty"):
        impl.allocate(100, [])


def test_error_negative_weight():
    """Any negative weight raises ValueError"""
    with pytest.raises(ValueError, match="negative"):
        impl.allocate(100, [1, 2, -1, 3])


def test_error_all_zero_weights():
    """All zero weights raises ValueError"""
    with pytest.raises(ValueError, match="zero"):
        impl.allocate(100, [0, 0, 0])


def test_error_validation_on_zero_amount():
    """Validation errors occur even when total_cents is zero"""
    with pytest.raises(ValueError, match="empty"):
        impl.allocate(0, [])
    with pytest.raises(ValueError, match="negative"):
        impl.allocate(0, [1, -1])
    with pytest.raises(ValueError, match="zero"):
        impl.allocate(0, [0, 0])
