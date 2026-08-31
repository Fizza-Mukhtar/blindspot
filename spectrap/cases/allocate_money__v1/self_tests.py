import pytest

import impl


def test_worked_example_from_ticket():
    assert impl.allocate(10, [1, 2, 4]) == [1, 3, 6]


def test_tie_break_lowest_index_first():
    assert impl.allocate(100, [1, 1, 1]) == [34, 33, 33]


def test_conservation_rule_various_inputs():
    cases = [
        (10, [1, 2, 4]),
        (100, [1, 1, 1]),
        (0, [1, 2, 3]),
        (1, [1, 1, 1, 1, 1]),
        (999, [7, 11, 13, 17]),
        (1000000, [1, 1, 1, 1, 1, 1, 1]),
    ]
    for total, weights in cases:
        result = impl.allocate(total, weights)
        assert sum(result) == total
        assert len(result) == len(weights)


def test_does_not_mutate_input_weights():
    weights = [1, 2, 4]
    original = list(weights)
    impl.allocate(10, weights)
    assert weights == original


def test_returns_new_list_object():
    weights = [1, 2, 4]
    result = impl.allocate(10, weights)
    assert result is not weights


def test_zero_weight_payee_gets_zero():
    result = impl.allocate(10, [0, 1, 1])
    assert result[0] == 0
    assert sum(result) == 10


def test_zero_total_returns_all_zeros():
    assert impl.allocate(0, [1, 2, 3]) == [0, 0, 0]


def test_negative_total_matches_negated_positive_allocation():
    positive = impl.allocate(10, [1, 2, 4])
    negative = impl.allocate(-10, [1, 2, 4])
    assert negative == [-x for x in positive]


def test_negative_total_specific_example_from_ticket():
    assert impl.allocate(-5, [1, 1]) == [-3, -2]


def test_negative_total_does_not_use_floor_division_bug():
    # -5 // 2 == -3 would wrongly yield [-2, -3]; correct answer negates
    # the positive-side allocation which gives the extra unit to index 0.
    result = impl.allocate(-5, [1, 1])
    assert result != [-2, -3]
    assert result == [-3, -2]


def test_negative_total_conservation():
    weights = [1, 2, 4]
    for total in (-10, -1, -999, -7):
        result = impl.allocate(total, weights)
        assert sum(result) == total


def test_single_payee_gets_everything():
    assert impl.allocate(10, [5]) == [10]
    assert impl.allocate(-10, [5]) == [-10]


def test_leftover_smaller_than_number_of_weights_no_double_serving():
    # weights all equal, total not evenly divisible: each payee gets at
    # most one extra unit above the floor.
    result = impl.allocate(7, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    floors = [0] * 10
    assert all(r in (0, 1) for r in result)
    assert sum(result) == 7


def test_empty_weights_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(10, [])


def test_negative_weight_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(10, [1, -1, 2])


def test_all_zero_weights_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(10, [0, 0, 0])


def test_validation_happens_even_for_zero_total():
    with pytest.raises(ValueError):
        impl.allocate(0, [])
    with pytest.raises(ValueError):
        impl.allocate(0, [0, 0])
    with pytest.raises(ValueError):
        impl.allocate(0, [1, -1])


def test_error_messages_mention_the_broken_rule():
    with pytest.raises(ValueError, match="empty"):
        impl.allocate(10, [])
    with pytest.raises(ValueError, match="negative"):
        impl.allocate(10, [1, -1])
    with pytest.raises(ValueError, match="positive"):
        impl.allocate(10, [0, 0])


def test_large_weights_exact_arithmetic_no_float_drift():
    # Weights and total chosen so floating point division would drift;
    # exact integer arithmetic must still conserve the total exactly.
    weights = [3, 3, 3, 1]
    total = 10**12 + 1
    result = impl.allocate(total, weights)
    assert sum(result) == total
    assert len(result) == 4
