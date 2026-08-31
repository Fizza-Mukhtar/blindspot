import impl
import pytest


def test_basic_allocation():
    """Test basic allocation with the example from the ticket."""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]
    assert sum(result) == 10


def test_sum_invariant():
    """Verify that sum of allocation equals total_cents."""
    assert sum(impl.allocate(100, [1, 1, 1])) == 100
    assert sum(impl.allocate(1000, [3, 7, 2])) == 1000
    assert sum(impl.allocate(42, [5, 5, 5, 5])) == 42


def test_zero_total():
    """Test that zero total returns all zeros."""
    result = impl.allocate(0, [1, 2, 3])
    assert result == [0, 0, 0]


def test_single_payee():
    """Test allocation with single payee."""
    result = impl.allocate(100, [1])
    assert result == [100]


def test_single_payee_negative():
    """Test negative allocation with single payee."""
    result = impl.allocate(-100, [1])
    assert result == [-100]


def test_equal_weights_even_split():
    """Test even split with equal weights."""
    result = impl.allocate(100, [1, 1, 1, 1])
    assert result == [25, 25, 25, 25]


def test_equal_weights_uneven_split():
    """Test uneven split with equal weights requires remainder distribution."""
    result = impl.allocate(10, [1, 1, 1])
    assert sum(result) == 10
    # Each gets 3, remainder 1 to first index
    assert result == [4, 3, 3]


def test_negative_allocation():
    """Test negative allocation negates the positive result."""
    positive = impl.allocate(10, [1, 2, 4])
    negative = impl.allocate(-10, [1, 2, 4])
    assert negative == [-x for x in positive]
    assert sum(negative) == -10


def test_zero_weight_payee():
    """Test that zero-weight payee gets exactly zero."""
    result = impl.allocate(100, [0, 1, 1])
    assert result[0] == 0
    assert sum(result) == 100


def test_multiple_zero_weights():
    """Test multiple zero-weight payees."""
    result = impl.allocate(50, [0, 0, 1, 1, 1])
    assert result[0] == 0
    assert result[1] == 0
    assert sum(result) == 50


def test_very_unequal_weights():
    """Test allocation with very unequal weights."""
    result = impl.allocate(100, [99, 1])
    assert result == [99, 1]


def test_no_mutation_of_input():
    """Verify that input list is not mutated."""
    weights = [1, 2, 3]
    weights_copy = weights.copy()
    impl.allocate(100, weights)
    assert weights == weights_copy


def test_empty_weights_raises():
    """Test that empty weights list raises ValueError."""
    with pytest.raises(ValueError, match="weights list cannot be empty"):
        impl.allocate(100, [])


def test_negative_weight_raises():
    """Test that negative weight raises ValueError."""
    with pytest.raises(ValueError, match="weights cannot contain negative values"):
        impl.allocate(100, [1, -1, 2])


def test_all_zero_weights_raises():
    """Test that all-zero weights raises ValueError."""
    with pytest.raises(ValueError, match="weights cannot all be zero"):
        impl.allocate(100, [0, 0, 0])


def test_validation_with_zero_total():
    """Test that validation happens even with zero total."""
    with pytest.raises(ValueError, match="weights cannot all be zero"):
        impl.allocate(0, [0, 0])


def test_tie_breaking_by_index():
    """Test that ties in remainders are broken by earliest index."""
    result = impl.allocate(10, [1, 1, 1, 1])
    # Each gets 2, all have remainder 2, leftover 2
    # First two indices get extra
    assert result == [3, 3, 2, 2]


def test_negative_odd_split():
    """Test negative allocation with remainder distribution."""
    positive = impl.allocate(5, [1, 1])
    negative = impl.allocate(-5, [1, 1])
    assert negative == [-x for x in positive]
    assert sum(negative) == -5


def test_remainder_distribution():
    """Test that larger remainders get allocated first."""
    # 101 with weights [3, 5, 2] has different remainders
    result = impl.allocate(101, [3, 5, 2])
    assert sum(result) == 101
    # Payee with weight 5 has largest remainder, gets the extra unit
    assert result == [30, 51, 20]


def test_no_payee_gains_more_than_one():
    """Verify no payee gets more than one extra unit."""
    result = impl.allocate(97, [5, 7, 3, 2])
    W = 17
    for i, w in enumerate([5, 7, 3, 2]):
        floor = (97 * w) // W
        assert result[i] <= floor + 1
        assert result[i] >= floor


def test_large_numbers():
    """Test with large numbers."""
    result = impl.allocate(1_000_000_000, [1, 2, 3])
    assert sum(result) == 1_000_000_000


def test_idempotent():
    """Verify that allocations are consistent (pure function)."""
    weights = [1, 2, 3]
    result1 = impl.allocate(100, weights)
    result2 = impl.allocate(100, weights)
    assert result1 == result2
