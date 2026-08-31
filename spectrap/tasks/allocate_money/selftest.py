"""Authoritative examples for LEDGER-238.

Every assertion here is traceable either to the Money pattern's ``allocate``
operation (https://martinfowler.com/eaaCatalog/money.html -- equivalently, the
largest-remainder / Hamilton apportionment method) or to an explicit sentence
of SPEC.md, never to whatever the reference implementation happens to do.
``make verify-corpus`` runs this against ``reference.py`` in CI, which is what
lets the README claim that ground-truth labels are verified by construction
rather than by inspection.
"""

import pytest

import impl

# (total_cents, weights) pairs used by the conservation properties below.
CASES = [
    (5, [1, 1]),
    (10, [1, 2, 4]),
    (100, [1, 1, 1]),
    (100, [404, 397, 199]),
    (11, [0, 1, 1]),
    (1, [1, 1, 1, 1, 1]),
    (0, [3, 4]),
    (7, [3]),
    (-5, [1, 1]),
    (-10, [1, 2, 4]),
    (-1, [1, 1, 1, 1, 1]),
    (-100, [404, 397, 199]),
    (123456789, [7, 11, 13, 17]),
]


@pytest.mark.parametrize("total,weights", CASES)
def test_conservation_the_parts_sum_to_the_whole(total, weights):
    """SPEC 'The conservation rule': sum(allocate(t, w)) == t, for every input."""
    assert sum(impl.allocate(total, weights)) == total


@pytest.mark.parametrize("total,weights", CASES)
def test_result_is_one_amount_per_payee(total, weights):
    """SPEC 'What to build': a new list, same length as weights, same order."""
    assert len(impl.allocate(total, weights)) == len(weights)


def test_fowler_five_cents_split_two_ways():
    """Money pattern: five cents two ways is 3 and 2, never 2 and 2 or 3 and 3."""
    assert impl.allocate(5, [1, 1]) == [3, 2]


def test_worked_example_from_the_ticket():
    """SPEC 'Worked example': allocate(10, [1, 2, 4]) == [1, 3, 6]."""
    assert impl.allocate(10, [1, 2, 4]) == [1, 3, 6]


def test_leftover_goes_to_the_largest_remainders_not_the_first_payees():
    """SPEC step 4: units go to the biggest fractional remainders first.

    Floors are [1, 2, 5] with remainders 3/7, 6/7, 5/7 and two units to place.
    Payees 1 and 2 hold the two largest remainders, so payee 0 -- who comes
    first in the list -- gains nothing.
    """
    result = impl.allocate(10, [1, 2, 4])
    assert result[0] == 1
    assert result[1] == 3 and result[2] == 6


def test_hamilton_apportionment_example():
    """Largest-remainder method: 100 units over claims 404/397/199.

    Exact shares are 40.4, 39.7 and 19.9; floors 40/39/19 leave two units, and
    the two largest remainders (.9 then .7) take them.
    """
    assert impl.allocate(100, [404, 397, 199]) == [40, 40, 20]


def test_tie_on_remainder_is_broken_by_lowest_index():
    """SPEC step 5: equal remainders -> the earlier index takes the unit."""
    assert impl.allocate(100, [1, 1, 1]) == [34, 33, 33]
    assert impl.allocate(5, [1, 1, 1, 1]) == [2, 1, 1, 1]


def test_no_payee_receives_more_than_one_extra_unit():
    """SPEC step 4: leftover units are handed out 'one each'.

    Every amount must be its own floor or that floor plus one.
    """
    total, weights = 7, [1, 1, 1]
    total_weight = sum(weights)
    result = impl.allocate(total, weights)
    for amount, weight in zip(result, weights):
        floor = (total * weight) // total_weight
        assert amount in (floor, floor + 1)


def test_zero_weight_receives_exactly_zero():
    """SPEC: 'A payee whose weight is 0 ... receives exactly 0'."""
    assert impl.allocate(11, [0, 1, 1]) == [0, 6, 5]
    assert impl.allocate(9, [0, 5, 0]) == [0, 9, 0]


def test_exact_division_leaves_no_remainder_to_distribute():
    """SPEC step 3: when the floors already sum to the total, nobody gains."""
    assert impl.allocate(100, [1, 1, 1, 1]) == [25, 25, 25, 25]
    assert impl.allocate(100, [3, 3, 4]) == [30, 30, 40]


def test_zero_total_pays_nobody():
    """SPEC 'Negative totals': allocate(0, weights) returns all zeros."""
    assert impl.allocate(0, [1, 2, 3]) == [0, 0, 0]
    assert impl.allocate(0, [0, 7]) == [0, 0]


def test_single_payee_takes_the_whole_amount():
    """Conservation rule with one share: the sum has only one term."""
    assert impl.allocate(7, [3]) == [7]
    assert impl.allocate(-7, [3]) == [-7]


@pytest.mark.parametrize("total,weights", CASES)
def test_negation_symmetry_for_negative_totals(total, weights):
    """SPEC 'Negative totals': allocate(-t, w) == [-x for x in allocate(t, w)]."""
    assert impl.allocate(-total, weights) == [-x for x in impl.allocate(total, weights)]


def test_negative_total_distributes_the_leftover_by_magnitude():
    """SPEC 'Negative totals': allocate(-5, [1, 1]) is [-3, -2], not [-2, -3]."""
    assert impl.allocate(-5, [1, 1]) == [-3, -2]
    assert impl.allocate(-10, [1, 2, 4]) == [-1, -3, -6]


def test_input_list_is_not_mutated():
    """SPEC 'What to build': 'Do not mutate the input.'"""
    weights = [1, 2, 4]
    impl.allocate(10, weights)
    assert weights == [1, 2, 4]


def test_empty_weights_raises_value_error():
    """SPEC 'Errors': weights is empty."""
    with pytest.raises(ValueError):
        impl.allocate(100, [])


def test_negative_weight_raises_value_error():
    """SPEC 'Errors': a payee cannot hold a negative claim."""
    with pytest.raises(ValueError):
        impl.allocate(100, [1, -1, 2])


def test_all_zero_weights_raises_value_error():
    """SPEC 'Errors': no basis on which to divide."""
    with pytest.raises(ValueError):
        impl.allocate(100, [0, 0, 0])


@pytest.mark.parametrize("total", [0, 5, -5])
def test_validation_runs_whatever_the_total_is(total):
    """SPEC 'Errors': 'applies whatever total_cents is, including 0'."""
    with pytest.raises(ValueError):
        impl.allocate(total, [0, 0])
