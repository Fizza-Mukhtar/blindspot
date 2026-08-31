import pytest
import impl


def test_empty_trace():
    """Empty trace returns empty list."""
    result = impl.simulate(capacity=10, refill_per_second=1, requests=[])
    assert result == []


def test_single_request_admitted():
    """Single request admitted when tokens available."""
    result = impl.simulate(capacity=10, refill_per_second=1, requests=[(0, 5)])
    assert result == [True]


def test_single_request_rejected():
    """Single request rejected when exceeds capacity."""
    result = impl.simulate(capacity=10, refill_per_second=1, requests=[(0, 15)])
    assert result == [False]


def test_single_request_exact_capacity():
    """Single request using exact capacity is admitted (1e-9 slack)."""
    result = impl.simulate(capacity=10, refill_per_second=1, requests=[(0, 10)])
    assert result == [True]


def test_multiple_requests_with_refill():
    """Requests admitted as tokens refill over time."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=1,
        requests=[(0, 5), (1, 3), (2, 1)]
    )
    assert result == [True, True, True]


def test_multiple_requests_with_rejection():
    """Request rejected when insufficient tokens, then admitted after refill."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=1,
        requests=[(0, 8), (0.5, 3), (1, 3)]
    )
    assert result == [True, False, True]


def test_cost_zero_always_admitted():
    """Zero cost is always admitted, even when bucket is empty."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=1,
        requests=[(0, 10), (0, 0), (0, 0)]
    )
    assert result == [True, True, True]


def test_cost_exceeds_capacity():
    """Cost exceeding capacity is never admitted, regardless of wait time."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=100,
        requests=[(0, 11), (1000, 11)]
    )
    assert result == [False, False]


def test_burst_at_same_timestamp():
    """Multiple requests at same timestamp accrue no tokens between them."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=1,
        requests=[(0, 5), (0, 3), (0, 2), (0, 1)]
    )
    assert result == [True, True, True, False]


def test_floating_point_slack():
    """1e-9 slack allows cost equal to tokens to be admitted."""
    result = impl.simulate(
        capacity=1,
        refill_per_second=1,
        requests=[(0, 1), (0.0000000001, 1)]
    )
    # First: tokens=1, cost=1 admitted, tokens=0
    # Second: after tiny elapsed time, tokens=1e-10, cost=1, 1e-10+1e-9 < 1, rejected
    assert result == [True, False]


def test_small_time_gaps_accumulate():
    """Small time gaps accumulate across multiple requests (40ms @ 5tok/s = 0.2 tokens)."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=5,
        requests=[(0, 9), (0.04, 0.5), (0.08, 0.5), (0.12, 0.5), (0.16, 0.5)]
    )
    # Bucket drains to 1, then each 0.04s gap gives 0.2 tokens
    # Sequence: +0.2, +0.2, +0.2, +0.2 = tokens rise from 1 to 1.8
    # Costs of 0.5 are all admissible except the last (0.3+1e-9 < 0.5)
    assert result == [True, True, True, True, False]


def test_capacity_invalid_negative():
    """ValueError when capacity is negative."""
    with pytest.raises(ValueError):
        impl.simulate(capacity=-1, refill_per_second=1, requests=[])


def test_refill_invalid_zero():
    """ValueError when refill_per_second is zero."""
    with pytest.raises(ValueError):
        impl.simulate(capacity=10, refill_per_second=0, requests=[])


def test_cost_invalid_negative():
    """ValueError when cost is negative."""
    with pytest.raises(ValueError):
        impl.simulate(capacity=10, refill_per_second=1, requests=[(0, -1)])


def test_timestamp_invalid_infinity():
    """ValueError when timestamp is infinite."""
    with pytest.raises(ValueError):
        impl.simulate(capacity=10, refill_per_second=1, requests=[(float('inf'), 1)])


def test_timestamp_not_non_decreasing():
    """ValueError when timestamps go backwards (corrupt trace)."""
    with pytest.raises(ValueError):
        impl.simulate(capacity=10, refill_per_second=1, requests=[(0, 1), (0.5, 1), (0.3, 1)])


def test_long_wait_refills_bucket_to_capacity():
    """Long wait allows bucket to refill to capacity cap."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=1,
        requests=[(0, 8), (10, 9)]
    )
    # t=0: tokens=10, cost=8, admitted, tokens=2
    # t=10: tokens=min(10, 2+10)=10, cost=9, admitted
    assert result == [True, True]


def test_bucket_clamped_to_zero():
    """Tokens clamped to 0 when cost equals remaining balance."""
    result = impl.simulate(
        capacity=10,
        refill_per_second=0.1,
        requests=[(0, 10), (0.1, 0.01), (0.2, 1)]
    )
    # t=0: tokens=10, cost=10, admitted, tokens=0
    # t=0.1: tokens=min(10, 0+0.01)=0.01, cost=0.01, admitted (0.01+1e-9>=0.01), tokens=0
    # t=0.2: tokens=min(10, 0+0.01)=0.01, cost=1, 0.01+1e-9<1, rejected
    assert result == [True, True, False]


def test_multiple_consecutive_rejections():
    """Multiple rejections followed by refill and eventual admission."""
    result = impl.simulate(
        capacity=5,
        refill_per_second=0.5,
        requests=[(0, 4), (0.1, 2), (0.2, 2), (2, 2)]
    )
    # t=0: tokens=5, cost=4, admitted, tokens=1
    # t=0.1: tokens=1+0.05=1.05, cost=2, rejected
    # t=0.2: tokens=1.05+0.05=1.1, cost=2, rejected
    # t=2: tokens=1.1+0.9=2, cost=2, admitted (2+1e-9>=2), tokens=0
    assert result == [True, False, False, True]
