import pytest
import impl
import math


# Validation: capacity
def test_validate_capacity_zero():
    """Capacity must be positive"""
    with pytest.raises(ValueError):
        impl.simulate(0, 1.0, [])


def test_validate_capacity_negative():
    """Capacity must be positive"""
    with pytest.raises(ValueError):
        impl.simulate(-5.0, 1.0, [])


def test_validate_capacity_nan():
    """Capacity must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(float('nan'), 1.0, [])


def test_validate_capacity_inf():
    """Capacity must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(float('inf'), 1.0, [])


# Validation: refill_per_second
def test_validate_refill_zero():
    """Refill rate must be positive"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 0, [(0, 1.0)])


def test_validate_refill_negative():
    """Refill rate must be positive"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, -1.0, [(0, 1.0)])


def test_validate_refill_nan():
    """Refill rate must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, float('nan'), [(0, 1.0)])


def test_validate_refill_inf():
    """Refill rate must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, float('inf'), [(0, 1.0)])


# Validation: timestamp
def test_validate_timestamp_nan():
    """Timestamp must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(float('nan'), 1.0)])


def test_validate_timestamp_inf():
    """Timestamp must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(float('inf'), 1.0)])


def test_validate_timestamp_decreasing():
    """Timestamps must be non-decreasing"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(1.0, 1.0), (0.5, 1.0)])


# Validation: cost
def test_validate_cost_negative():
    """Cost must be non-negative"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(0, -1.0)])


def test_validate_cost_nan():
    """Cost must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(0, float('nan'))])


def test_validate_cost_inf():
    """Cost must be finite"""
    with pytest.raises(ValueError):
        impl.simulate(10.0, 1.0, [(0, float('inf'))])


# Basic functionality
def test_empty_trace():
    """Empty trace returns empty list"""
    assert impl.simulate(10.0, 1.0, []) == []


def test_single_admission():
    """Single request within capacity admitted"""
    assert impl.simulate(10.0, 1.0, [(0, 5.0)]) == [True]


def test_single_rejection():
    """Single request exceeding capacity rejected"""
    assert impl.simulate(10.0, 1.0, [(0, 15.0)]) == [False]


def test_bucket_starts_at_capacity():
    """Bucket initialized to capacity"""
    assert impl.simulate(10.0, 1.0, [(0, 10.0)]) == [True]


def test_zero_cost_always_admitted():
    """Zero cost always admitted regardless of bucket state"""
    assert impl.simulate(10.0, 1.0, [(0, 10.0), (0, 0.0)]) == [True, True]


# Refill and accrual
def test_refill_over_time():
    """Tokens refill over time between requests"""
    # Admit 8 (2 left), wait 1 sec at 1 token/sec (3 total), admit 2
    result = impl.simulate(10.0, 1.0, [(0, 8.0), (1.0, 2.0)])
    assert result == [True, True]


def test_refill_capped_at_capacity():
    """Refilled tokens never exceed capacity"""
    # Admit 5 (5 left), wait 100 sec (would refill 100, capped at 10), admit 10
    result = impl.simulate(10.0, 1.0, [(0, 5.0), (100.0, 10.0)])
    assert result == [True, True]


def test_fractional_refill():
    """Fractional time gaps produce fractional refill"""
    # Admit 5 (5 left), wait 0.04 sec at 5/sec (5+0.2=5.2 total), admit 1
    result = impl.simulate(10.0, 5.0, [(0, 5.0), (0.04, 1.0)])
    assert result == [True, True]


def test_rejected_request_preserves_tokens():
    """Rejected request leaves token count unchanged"""
    # Reject 15 (bucket unchanged at 10), wait 1 sec (10+1=11, capped at 10), admit 10
    result = impl.simulate(10.0, 1.0, [(0, 15.0), (1.0, 10.0)])
    assert result == [False, True]


# Burst behavior (same timestamp)
def test_burst_no_refill_between():
    """Burst at same timestamp has no refill between requests"""
    assert impl.simulate(10.0, 1.0, [(0, 5.0), (0, 5.0)]) == [True, True]


def test_burst_exceeds_capacity():
    """Second request in burst rejected if combined > capacity"""
    assert impl.simulate(10.0, 1.0, [(0, 8.0), (0, 3.0)]) == [True, False]


def test_burst_three_requests():
    """Three requests at same instant"""
    result = impl.simulate(10.0, 1.0, [(0, 3.0), (0, 3.0), (0, 4.0)])
    assert result == [True, True, True]


# Edge cases
def test_cost_exceeds_capacity_never_admitted():
    """Cost > capacity never admitted, even with waiting"""
    result = impl.simulate(10.0, 1.0, [(0, 11.0), (1000.0, 11.0)])
    assert result == [False, False]


def test_cost_exactly_capacity():
    """Cost exactly equal to capacity admitted"""
    assert impl.simulate(10.0, 1.0, [(0, 10.0)]) == [True]


def test_floating_point_slack():
    """1e-9 slack allows cost very close to tokens"""
    # Cost is capacity + slightly less than 1e-9 slack
    capacity = 10.0
    cost = capacity + 0.5e-9
    result = impl.simulate(capacity, 1.0, [(0, cost)])
    assert result == [True]


def test_zero_cost_with_empty_bucket():
    """Zero cost admitted even when bucket empty"""
    result = impl.simulate(10.0, 1.0, [(0, 10.0), (0, 0.0), (0, 1.0)])
    assert result == [True, True, False]


# Numeric types
def test_int_inputs():
    """Integer inputs accepted and converted"""
    assert impl.simulate(10, 1, [(0, 5)]) == [True]


# Complex scenarios
def test_steady_stream_under_capacity():
    """Steady stream of requests below refill rate accumulates"""
    # Capacity 100, refill 10/sec, requests 5 every 1 sec
    result = impl.simulate(100.0, 10.0, [
        (0, 5.0), (1.0, 5.0), (2.0, 5.0)
    ])
    assert result == [True, True, True]


def test_throttled_during_burst():
    """Some requests in burst throttled when capacity exhausted"""
    # Capacity 10, refill 5/sec
    result = impl.simulate(10.0, 5.0, [
        (0, 5.0),      # admit 5, 5 left
        (0, 5.0),      # admit 5, 0 left
        (0, 1.0),      # reject (0 tokens)
        (0.2, 1.0),    # admit (0 + 0.2*5 = 1.0), 0 left
    ])
    assert result == [True, True, False, True]
