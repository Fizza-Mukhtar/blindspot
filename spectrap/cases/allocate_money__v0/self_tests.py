import pytest

import impl


def test_worked_example_from_ticket():
    assert impl.allocate(10, [1, 2, 4]) == [1, 3, 6]


def test_tie_breaks_by_lowest_index():
    assert impl.allocate(100, [1, 1, 1]) == [34, 33, 33]


def test_negative_total_matches_ticket_example():
    assert impl.allocate(-5, [1, 1]) == [-3, -2]


def test_negative_equals_negated_positive_for_various_inputs():
    cases = [
        (10, [1, 2, 4]),
        (100, [1, 1, 1]),
        (7, [3, 5, 2]),
        (1, [1, 1, 1, 1]),
        (0, [1, 2, 3]),
    ]
    for total, weights in cases:
        positive = impl.allocate(total, weights)
        negative = impl.allocate(-total, weights)
        assert negative == [-x for x in positive]


def test_zero_total_returns_all_zeros():
    assert impl.allocate(0, [1, 2, 3]) == [0, 0, 0]


def test_sum_conserved_for_many_positive_combinations():
    totals = [0, 1, 2, 5, 10, 99, 1000, 7]
    weight_sets = [
        [1],
        [1, 1],
        [1, 2, 4],
        [3, 5, 2],
        [0, 1, 2],
        [10, 10, 10, 10, 10, 10, 10],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
    ]
    for total in totals:
        for weights in weight_sets:
            result = impl.allocate(total, weights)
            assert sum(result) == total
            assert len(result) == len(weights)


def test_sum_conserved_for_negative_totals():
    totals = [-1, -2, -5, -10, -99, -1000, -7]
    weight_sets = [
        [1, 1],
        [1, 2, 4],
        [3, 5, 2],
        [0, 1, 2],
    ]
    for total in totals:
        for weights in weight_sets:
            result = impl.allocate(total, weights)
            assert sum(result) == total


def test_zero_weight_payee_gets_nothing():
    result = impl.allocate(10, [0, 1, 1])
    assert result[0] == 0
    assert sum(result) == 10


def test_all_zero_weight_payees_with_zero_others_still_correct():
    result = impl.allocate(50, [0, 0, 5])
    assert result == [0, 0, 50]


def test_single_payee_gets_entire_total():
    assert impl.allocate(123, [7]) == [123]
    assert impl.allocate(-123, [7]) == [-123]


def test_does_not_mutate_input_weights():
    weights = [1, 2, 4]
    original = list(weights)
    impl.allocate(10, weights)
    assert weights == original


def test_returns_new_list_not_same_object():
    weights = [1, 2, 4]
    result = impl.allocate(10, weights)
    assert result is not weights


def test_empty_weights_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(100, [])


def test_empty_weights_raises_even_for_zero_total():
    with pytest.raises(ValueError):
        impl.allocate(0, [])


def test_negative_weight_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(100, [1, -1, 2])


def test_all_zero_weights_raises_value_error():
    with pytest.raises(ValueError):
        impl.allocate(100, [0, 0, 0])


def test_all_zero_weights_raises_even_for_zero_total():
    with pytest.raises(ValueError):
        impl.allocate(0, [0, 0])


def test_large_total_with_uneven_weights_conserves_and_orders_remainders_correctly():
    # W = 13, total = 1000
    # weight 1: 1000*1=1000, 1000//13=76, rem=12
    # weight 5: 1000*5=5000, 5000//13=384, rem=8
    # weight 7: 1000*7=7000, 7000//13=538, rem=6
    # floors sum = 76+384+538 = 998, leftover = 2
    # largest remainders: index0 (12), index1 (8) get the extra units
    result = impl.allocate(1000, [1, 5, 7])
    assert result == [77, 385, 538]
    assert sum(result) == 1000


def test_leftover_never_exceeds_number_of_nonzero_remainder_payees():
    # weights all equal, total not divisible evenly, ensure no double allocation
    result = impl.allocate(11, [1, 1, 1, 1, 1])
    # floor each = 2, remainder each = 1 (11*1=11, 11//5=2, 11%5=1)
    # leftover = 11 - 10 = 1, only index 0 gets it due to tie-break
    assert result == [3, 2, 2, 2, 2]
    assert sum(result) == 11
