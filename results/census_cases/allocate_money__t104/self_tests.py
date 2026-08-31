import pytest
import impl


def test_example_from_spec():
    """Test the example given in the specification."""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]


def test_zero_total():
    """Zero total returns all zeros."""
    result = impl.allocate(0, [1, 2, 3])
    assert result == [0, 0, 0]


def test_single_payee():
    """Single payee gets entire amount."""
    assert impl.allocate(10, [1]) == [10]
    assert impl.allocate(-10, [1]) == [-10]
    assert impl.allocate(0, [1]) == [0]


def test_zero_weight_payee():
    """Payee with zero weight gets nothing."""
    result = impl.allocate(10, [0, 1, 2])
    assert result[0] == 0
    assert sum(result) == 10
    assert result == [0, 3, 7]


def test_negative_total_from_spec():
    """Test negative total example: allocate(-5, [1, 1]) == [-3, -2]."""
    result = impl.allocate(-5, [1, 1])
    assert result == [-3, -2]


def test_negative_is_negation_of_positive():
    """Negative allocation is negation of positive allocation."""
    pos = impl.allocate(10, [1, 2, 3])
    neg = impl.allocate(-10, [1, 2, 3])
    assert neg == [-x for x in pos]


def test_equal_weights_remainder_distribution():
    """Equal weights distribute remainders by index order."""
    # Three equal weights, 10 units: 10/3 = 3 remainder 1
    # Index 0 gets the extra unit
    result = impl.allocate(10, [1, 1, 1])
    assert result == [4, 3, 3]
    
    # Three equal weights, 11 units: 11/3 = 3 remainder 2
    # Indices 0 and 1 get extra units (tie-breaking by index)
    result = impl.allocate(11, [1, 1, 1])
    assert result == [4, 4, 3]


def test_largest_remainder_priority():
    """Largest remainders get distributed first."""
    result = impl.allocate(10, [1, 3, 2])
    # W=6: floors=[1,5,3], remainders=[4,0,2]
    # 1 unit left, goes to payee with largest remainder (index 0)
    assert result == [2, 5, 3]
    assert sum(result) == 10


def test_empty_weights_error():
    """Empty weights list raises ValueError."""
    with pytest.raises(ValueError, match="weights list cannot be empty"):
        impl.allocate(10, [])


def test_negative_weight_error():
    """Negative weight raises ValueError."""
    with pytest.raises(ValueError, match="all weights must be non-negative"):
        impl.allocate(10, [1, -1, 2])


def test_all_zero_weights_error():
    """All zero weights raises ValueError."""
    with pytest.raises(ValueError, match="at least one weight must be positive"):
        impl.allocate(10, [0, 0, 0])


def test_validation_with_zero_total():
    """Validation happens before allocation even with zero total."""
    with pytest.raises(ValueError, match="weights list cannot be empty"):
        impl.allocate(0, [])
    
    with pytest.raises(ValueError, match="at least one weight must be positive"):
        impl.allocate(0, [0, 0])
    
    with pytest.raises(ValueError, match="all weights must be non-negative"):
        impl.allocate(0, [1, -1])


def test_sum_invariant():
    """Sum of allocation always equals total."""
    test_cases = [
        (100, [1, 2, 3]),
        (99, [7, 11, 13]),
        (-100, [1, 2, 3]),
        (1, [1, 1, 1]),
        (10, [1, 2, 4]),
        (0, [1, 1]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total, f"Sum failed for allocate({total}, {weights})"


def test_length_invariant():
    """Result length equals weights length."""
    test_cases = [
        (10, [1, 2]),
        (100, [1, 2, 3, 4, 5]),
        (0, [7, 8, 9]),
        (50, [1]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert len(result) == len(weights)


def test_no_mutation():
    """Original weights list is not mutated."""
    weights = [1, 2, 3]
    weights_copy = weights.copy()
    impl.allocate(10, weights)
    assert weights == weights_copy


def test_large_numbers():
    """Handle large total and weight values."""
    result = impl.allocate(1000000, [1000, 2000, 3000])
    assert sum(result) == 1000000
    assert len(result) == 3


def test_edge_case_one_unit():
    """Verify handling when only one unit can be distributed."""
    result = impl.allocate(1, [1, 1, 1])
    assert result == [1, 0, 0]
    assert sum(result) == 1
