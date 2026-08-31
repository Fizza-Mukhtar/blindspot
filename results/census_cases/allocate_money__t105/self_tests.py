import pytest
import impl


def test_allocate_spec_example():
    """Test the example from the spec: 10 across [1, 2, 4] gives [1, 3, 6]."""
    assert impl.allocate(10, [1, 2, 4]) == [1, 3, 6]


def test_allocate_sum_property():
    """sum(allocate(...)) == total_cents always holds."""
    test_cases = [
        (10, [1, 2, 4]),
        (5, [1, 1]),
        (0, [1, 2, 3]),
        (-10, [1, 2, 4]),
        (100, [7, 3, 11]),
        (1, [1, 1, 1, 1, 1]),
    ]
    for total, weights in test_cases:
        assert sum(impl.allocate(total, weights)) == total


def test_allocate_negative_example():
    """Test spec example with negative: allocate(-5, [1, 1]) should be [-3, -2]."""
    assert impl.allocate(-5, [1, 1]) == [-3, -2]


def test_allocate_zero_total():
    """Zero total returns all zeros regardless of weights."""
    assert impl.allocate(0, [1, 2, 3]) == [0, 0, 0]
    assert impl.allocate(0, [5]) == [0]
    assert impl.allocate(0, [1, 0, 2]) == [0, 0, 0]


def test_allocate_single_payee():
    """Single payee gets the entire amount."""
    assert impl.allocate(100, [1]) == [100]
    assert impl.allocate(-50, [1]) == [-50]


def test_allocate_equal_weights():
    """Payees with equal weights split proportionally."""
    assert impl.allocate(10, [1, 1]) == [5, 5]
    assert impl.allocate(9, [1, 1, 1]) == [3, 3, 3]
    result = impl.allocate(5, [1, 1, 1, 1, 1])
    assert result == [1, 1, 1, 1, 1]


def test_allocate_exact_division():
    """Total divides evenly with no remainder distribution."""
    assert impl.allocate(6, [1, 2, 3]) == [1, 2, 3]
    assert impl.allocate(100, [1, 1, 1, 1]) == [25, 25, 25, 25]


def test_allocate_with_zero_weight():
    """Zero weight receives nothing."""
    result = impl.allocate(10, [1, 0, 2])
    assert result[1] == 0
    assert sum(result) == 10


def test_allocate_remainder_distribution():
    """Leftover units go to payees with largest remainders."""
    # 10 across [3, 3, 1]: floors [4, 4, 1], remainders [2/7, 2/7, 3/7]
    # One unit leftover goes to payee with largest remainder (payee 2)
    result = impl.allocate(10, [3, 3, 1])
    assert sum(result) == 10
    # Payee 2 should have gotten the extra unit
    assert result[2] == 2


def test_allocate_tie_breaking_by_index():
    """When remainders are equal, earlier index gets priority."""
    # 7 across [1, 1, 1, 1, 1]: floors all 1, remainders all 2/5
    # 2 units leftover go to payees with largest remainders
    result = impl.allocate(7, [1, 1, 1, 1, 1])
    assert sum(result) == 7
    # Two payees get 2, three get 1; payees 0 and 1 get priority by index
    assert result[0] == 2
    assert result[1] == 2
    assert result[2] == 1
    assert result[3] == 1
    assert result[4] == 1


def test_allocate_negative_reverses():
    """Negative totals negate the positive allocation."""
    positive = impl.allocate(10, [1, 2, 4])
    negative = impl.allocate(-10, [1, 2, 4])
    assert negative == [-x for x in positive]


def test_allocate_large_numbers():
    """Large numbers are handled correctly."""
    result = impl.allocate(1000000, [1, 2, 3])
    assert sum(result) == 1000000
    assert len(result) == 3


def test_allocate_result_length():
    """Result list has same length as weights."""
    assert len(impl.allocate(10, [1, 2, 4])) == 3
    assert len(impl.allocate(0, [1])) == 1
    assert len(impl.allocate(100, [1, 1, 1, 1, 1])) == 5


def test_allocate_empty_weights_error():
    """Empty weights list raises ValueError."""
    with pytest.raises(ValueError, match="weights cannot be empty"):
        impl.allocate(10, [])
    
    with pytest.raises(ValueError):
        impl.allocate(0, [])


def test_allocate_negative_weight_error():
    """Negative weight raises ValueError."""
    with pytest.raises(ValueError, match="all weights must be non-negative"):
        impl.allocate(10, [1, -1, 2])
    
    with pytest.raises(ValueError):
        impl.allocate(0, [1, -1])


def test_allocate_all_zero_weights_error():
    """All zero weights raises ValueError."""
    with pytest.raises(ValueError, match="at least one weight must be non-zero"):
        impl.allocate(10, [0, 0, 0])
    
    with pytest.raises(ValueError):
        impl.allocate(0, [0, 0])


def test_allocate_input_not_mutated():
    """Input lists are not mutated."""
    weights = [1, 2, 4]
    weights_copy = weights.copy()
    impl.allocate(10, weights)
    assert weights == weights_copy
