import pytest
import impl


# === Basic Functionality ===

def test_empty_trace():
    """Empty trace returns empty list."""
    result = impl.simulate(10.0, 1.0, [])
    assert result == []


def test_single_request_admitted():
    """Single request within capacity is admitted."""
    result = impl.simulate(10.0, 1.0, [(0.0, 5.0)])
    assert result == [True]


def test_single_request_rejected():
    """Single request exceeding capacity is rejected."""
    result = impl.simulate(10.0, 1.0, [(0.0, 15.0)])
    assert result == [False]


def test_multiple_requests_with_refill():
    """Multiple requests with time gaps allowing refill."""
    # Capacity 10, refill 2/sec, bucket starts full
    # t=0: 10 tokens, cost 5 → admitted, 5 left
    # t=3: 5 + 6 = 11 (capped at 10), cost 8 → admitted, 2 left
    # t=5: 2 + 4 = 6, cost 3 → admitted, 3 left
    result = impl.simulate(10.0, 2.0, [(0.0, 5.0), (3.0, 8.0), (5.0, 3.0)])
    assert result == [True, True, True]


def test_cost_zero_admitted():
    """Cost of zero is always admitted."""
    # First request uses all tokens, second has zero cost
    result = impl.simulate(1.0, 0.1, [(0.0, 1.0), (0.0, 0.0)])
    assert result == [True, True]


def test_simultaneous_requests_burst():
    """Multiple requests at same timestamp don't accrue tokens between them."""
    # t=0: capacity 10, cost 3 → admitted, 7 left
    # t=0: cost 3 → admitted, 4 left
    # t=0: cost 5 → rejected (only 4 tokens left)
    result = impl.simulate(10.0, 1.0, [(0.0, 3.0), (0.0, 3.0), (0.0, 5.0)])
    assert result == [True, True, False]


def test_rejected_request_no_consumption():
    """Rejected request doesn't consume tokens."""
    # t=0: capacity 5, cost 6 → rejected, 5 tokens remain
    # t=0: cost 3 → admitted (5 tokens available)
    result = impl.simulate(5.0, 1.0, [(0.0, 6.0), (0.0, 3.0)])
    assert result == [False, True]


def test_bucket_caps_at_capacity():
    """Bucket is capped at capacity, doesn't overfill."""
    # Capacity 10, refill 100/sec, large time gap
    # After 1 second, bucket should still be 10, not 100+
    result = impl.simulate(10.0, 100.0, [(0.0, 1.0), (1.0, 9.0)])
    assert result == [True, True]


def test_floating_point_slack_within_boundary():
    """Floating-point slack of 1e-9 allows admission at boundary."""
    # Cost 10 + 1e-10 is within 1e-9 slack, should be admitted
    result = impl.simulate(10.0, 1.0, [(0.0, 10.0 + 1e-10)])
    assert result == [True]


def test_small_gaps_accumulate():
    """Small time gaps accumulate to refill tokens gradually."""
    # 0.04 sec at 5 tokens/sec = 0.2 tokens per gap
    # Five gaps = 1.0 token accumulated
    requests = [(0.0, 1.0), (0.04, 1.0), (0.08, 1.0), (0.12, 1.0), (0.16, 1.0)]
    result = impl.simulate(10.0, 5.0, requests)
    assert result == [True, True, True, True, True]


# === Error Validation ===

def test_capacity_zero_invalid():
    """capacity = 0 raises ValueError."""
    with pytest.raises(ValueError, match="capacity must be a finite number greater than zero"):
        impl.simulate(0.0, 1.0, [])


def test_capacity_infinity_invalid():
    """capacity = infinity raises ValueError."""
    with pytest.raises(ValueError, match="capacity must be a finite number greater than zero"):
        impl.simulate(float('inf'), 1.0, [])


def test_capacity_nan_invalid():
    """capacity = NaN raises ValueError."""
    with pytest.raises(ValueError, match="capacity must be a finite number greater than zero"):
        impl.simulate(float('nan'), 1.0, [])


def test_refill_zero_invalid():
    """refill_per_second = 0 raises ValueError."""
    with pytest.raises(ValueError, match="refill_per_second must be a finite number greater than zero"):
        impl.simulate(10.0, 0.0, [])


def test_refill_infinity_invalid():
    """refill_per_second = infinity raises ValueError."""
    with pytest.raises(ValueError, match="refill_per_second must be a finite number greater than zero"):
        impl.simulate(10.0, float('inf'), [])


def test_timestamp_infinity_invalid():
    """timestamp = infinity raises ValueError."""
    with pytest.raises(ValueError, match="timestamp must be a finite number"):
        impl.simulate(10.0, 1.0, [(float('inf'), 1.0)])


def test_timestamp_decreasing_invalid():
    """timestamp < previous timestamp raises ValueError."""
    with pytest.raises(ValueError, match="timestamps must be non-decreasing"):
        impl.simulate(10.0, 1.0, [(1.0, 1.0), (0.5, 1.0)])


def test_cost_negative_invalid():
    """cost < 0 raises ValueError."""
    with pytest.raises(ValueError, match="cost must not be negative"):
        impl.simulate(10.0, 1.0, [(0.0, -1.0)])


def test_cost_infinity_invalid():
    """cost = infinity raises ValueError."""
    with pytest.raises(ValueError, match="cost must be a finite number"):
        impl.simulate(10.0, 1.0, [(0.0, float('inf'))])


def test_cost_nan_invalid():
    """cost = NaN raises ValueError."""
    with pytest.raises(ValueError, match="cost must be a finite number"):
        impl.simulate(10.0, 1.0, [(0.0, float('nan'))])
