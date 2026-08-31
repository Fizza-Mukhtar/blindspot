import pytest
import impl


def test_allocate_basic_example():
    """Test the ticket example: allocate(10, [1, 2, 4]) -> [1, 3, 6]"""
    result = impl.allocate(10, [1, 2, 4])
    assert result == [1, 3, 6]
    assert sum(result) == 10


def test_allocate_single_payee():
    """Single payee receives entire amount."""
    result = impl.allocate(100, [1])
    assert result == [100]
    result = impl.allocate(100, [5])
    assert result == [100]


def test_allocate_equal_weights():
    """Equal weights divide as evenly as possible."""
    result = impl.allocate(10, [1, 1, 1])
    assert result == [4, 3, 3]
    assert sum(result) == 10
    
    result = impl.allocate(5, [1, 1])
    assert result == [3, 2]


def test_allocate_zero_total():
    """Zero total returns all zeros."""
    assert impl.allocate(0, [1, 2, 3]) == [0, 0, 0]
    assert impl.allocate(0, [1]) == [0]
    assert impl.allocate(0, [1, 1, 1, 1]) == [0, 0, 0, 0]


def test_allocate_negative_total():
    """Negative total negates the positive allocation result."""
    positive = impl.allocate(10, [1, 2, 4])
    negative = impl.allocate(-10, [1, 2, 4])
    assert negative == [-x for x in positive]
    
    result = impl.allocate(-5, [1, 1])
    assert result == [-3, -2]
    assert sum(result) == -5


def test_allocate_with_zero_weights():
    """Zero-weight payees receive nothing."""
    result = impl.allocate(10, [0, 1])
    assert result == [0, 10]
    
    result = impl.allocate(20, [0, 2, 0, 3])
    assert result == [0, 8, 0, 12]
    
    result = impl.allocate(-15, [1, 0, 2, 0])
    assert result[1] == 0
    assert result[3] == 0
    assert sum(result) == -15


def test_allocate_tie_breaking():
    """Tie-breaking by index for equal remainders."""
    result = impl.allocate(7, [1, 1, 1])
    assert result == [3, 2, 2]
    
    result = impl.allocate(11, [1, 2, 3])
    assert result == [2, 4, 5]
    assert sum(result) == 11


def test_allocate_error_empty_weights():
    """Empty weights raises ValueError."""
    with pytest.raises(ValueError, match="weights cannot be empty"):
        impl.allocate(10, [])


def test_allocate_error_negative_weight():
    """Negative weight raises ValueError."""
    with pytest.raises(ValueError, match="weights cannot contain negative values"):
        impl.allocate(10, [1, -1, 2])


def test_allocate_error_all_zero_weights():
    """All-zero weights raise ValueError."""
    with pytest.raises(ValueError, match="weights cannot all be zero"):
        impl.allocate(10, [0, 0, 0])


def test_allocate_validation_before_allocation():
    """Validation occurs even with zero or negative total."""
    with pytest.raises(ValueError, match="weights cannot be empty"):
        impl.allocate(0, [])
    
    with pytest.raises(ValueError, match="weights cannot contain negative values"):
        impl.allocate(0, [1, -1])
    
    with pytest.raises(ValueError, match="weights cannot all be zero"):
        impl.allocate(-10, [0, 0])


def test_allocate_sum_property():
    """Sum always equals input total."""
    test_cases = [
        (100, [1, 2, 3]),
        (27, [3, 5, 7]),
        (-50, [2, 3, 5]),
        (1, [1, 1, 1, 1]),
        (99, [1, 0, 1, 0, 1]),
    ]
    for total, weights in test_cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total, f"Failed for total={total}, weights={weights}"


def test_allocate_length_property():
    """Result length matches weights length."""
    assert len(impl.allocate(100, [1, 2, 3, 4, 5])) == 5
    assert len(impl.allocate(0, [1])) == 1
    assert len(impl.allocate(-50, [1, 1, 1])) == 3


def test_allocate_no_input_mutation():
    """Input weights are not modified."""
    weights = [1, 2, 3]
    original = weights.copy()
    impl.allocate(100, weights)
    assert weights == original


def test_allocate_deterministic():
    """Same input always produces same output."""
    expected = impl.allocate(17, [3, 5, 2])
    for _ in range(5):
        assert impl.allocate(17, [3, 5, 2]) == expected


def test_allocate_large_values():
    """Handles large totals and weights correctly."""
    result = impl.allocate(1000000, [1, 2, 3])
    assert sum(result) == 1000000
    
    result = impl.allocate(100, [1000000, 2000000])
    assert sum(result) == 100


def test_allocate_one_unit_many_payees():
    """Single unit among many equal payees goes to first."""
    result = impl.allocate(1, [1, 1, 1, 1, 1])
    assert sum(result) == 1
    assert result[0] == 1
    assert all(x == 0 for x in result[1:])


def test_allocate_bounded_difference():
    """No payee receives more than one extra unit."""
    result = impl.allocate(100, [1, 1, 1, 1])
    assert max(result) - min(result) <= 1
    
    result = impl.allocate(17, [1, 1, 1])
    assert max(result) - min(result) <= 1
