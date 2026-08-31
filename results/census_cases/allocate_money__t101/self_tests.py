import pytest
import impl


def test_single_payee():
    """Single payee receives entire amount."""
    result = impl.allocate(100, [1])
    assert result == [100]
    assert sum(result) == 100


def test_even_split():
    """Two payees with equal weights split evenly."""
    result = impl.allocate(10, [1, 1])
    assert result == [5, 5]
    assert sum(result) == 10


def test_uneven_split():
    """Two payees with unequal weights split proportionally."""
    result = impl.allocate(10, [1, 3])
    assert result == [3, 7]
    assert sum(result) == 10


def test_ticket_example():
    """Verify the example from ticket: allocate(10, [1, 2, 4]) = [1, 3, 6]."""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]
    assert sum(result) == 10


def test_zero_total():
    """Zero total allocates zero to all payees."""
    result = impl.allocate(0, [1, 2, 3])
    assert result == [0, 0, 0]
    assert sum(result) == 0


def test_three_way_split():
    """Three payees with equal weights - leftover to earliest index."""
    result = impl.allocate(10, [1, 1, 1])
    assert result == [4, 3, 3]
    assert sum(result) == 10


def test_exact_division():
    """Allocation that divides evenly with no remainder."""
    result = impl.allocate(12, [1, 2, 3])
    assert result == [2, 4, 6]
    assert sum(result) == 12


def test_negative_total():
    """Negative total is negation of positive allocation."""
    pos = impl.allocate(10, [1, 2, 4])
    neg = impl.allocate(-10, [1, 2, 4])
    assert neg == [-x for x in pos]
    assert sum(neg) == -10


def test_negative_with_tie_remainder():
    """Negative allocation with tied remainders - earliest index priority."""
    result = impl.allocate(-5, [1, 1])
    assert result == [-3, -2]
    assert sum(result) == -5


def test_zero_weights():
    """Payees with zero weight receive exactly zero."""
    result = impl.allocate(10, [0, 1, 2])
    assert result == [0, 3, 7]
    assert sum(result) == 10
    
    result = impl.allocate(-10, [0, 1, 2])
    assert result == [0, -3, -7]
    assert sum(result) == -10


def test_empty_weights_error():
    """Empty weights list raises ValueError."""
    with pytest.raises(ValueError, match="empty"):
        impl.allocate(10, [])


def test_negative_weight_error():
    """Negative weight raises ValueError."""
    with pytest.raises(ValueError, match="negative"):
        impl.allocate(10, [1, -1, 2])


def test_all_zero_weights_error():
    """All zero weights raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        impl.allocate(10, [0, 0, 0])


def test_validation_before_allocation():
    """Validation happens even with zero total."""
    with pytest.raises(ValueError, match="empty"):
        impl.allocate(0, [])
    
    with pytest.raises(ValueError, match="positive"):
        impl.allocate(0, [0, 0])


def test_sum_invariant_holds():
    """Sum of allocation always equals total for all test cases."""
    test_cases = [
        (100, [1]),
        (50, [1, 1]),
        (99, [1, 2, 3]),
        (1000, [7, 11, 13]),
        (1, [1, 1]),
        (11, [1, 1, 1, 1, 1, 1]),
        (-100, [1]),
        (-99, [1, 2, 3]),
        (0, [1, 2, 3]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total, f"Failed for allocate({total}, {weights}): {result}"
        assert len(result) == len(weights)


def test_no_input_mutation():
    """Function does not mutate input lists."""
    weights = [1, 2, 3]
    weights_copy = weights.copy()
    impl.allocate(100, weights)
    assert weights == weights_copy


def test_large_numbers():
    """Handle large allocation amounts."""
    result = impl.allocate(1000000000, [1, 1])
    assert sum(result) == 1000000000
    assert result == [500000000, 500000000]


def test_many_payees():
    """Many payees with equal weights distribute evenly."""
    weights = [1] * 100
    result = impl.allocate(1000, weights)
    assert sum(result) == 1000
    assert len(result) == 100
    assert all(x == 10 for x in result)


def test_remainder_tie_breaking_by_index():
    """When remainders tie, earlier index gets the leftover unit."""
    result = impl.allocate(7, [1, 1, 1])
    assert result == [3, 2, 2]
    assert sum(result) == 7
