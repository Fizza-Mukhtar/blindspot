def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    """
    Simulate a token bucket rate limiter over a recorded request trace.
    
    Args:
        capacity: Bucket size in tokens (must be finite and > 0)
        refill_per_second: Rate at which credit accrues (must be finite and > 0)
        requests: List of (timestamp_seconds, cost) tuples
    
    Returns:
        List of booleans, one per request, True if admitted, False if rejected
    
    Raises:
        ValueError: If parameters are invalid or trace is out of order
    """
    import math
    
    # Validate capacity
    try:
        is_finite = math.isfinite(capacity)
    except TypeError:
        is_finite = False
    
    if not is_finite or capacity <= 0:
        raise ValueError("capacity must be a finite number greater than zero")
    
    # Validate refill_per_second
    try:
        is_finite = math.isfinite(refill_per_second)
    except TypeError:
        is_finite = False
    
    if not is_finite or refill_per_second <= 0:
        raise ValueError("refill_per_second must be a finite number greater than zero")
    
    if not requests:
        return []
    
    results = []
    tokens = capacity
    prev_timestamp = None
    
    for timestamp, cost in requests:
        # Validate timestamp
        try:
            is_finite = math.isfinite(timestamp)
        except TypeError:
            is_finite = False
        
        if not is_finite:
            raise ValueError("timestamp must be a finite number")
        
        if prev_timestamp is not None and timestamp < prev_timestamp:
            raise ValueError("timestamps must be non-decreasing")
        
        # Validate cost
        try:
            is_finite = math.isfinite(cost)
        except TypeError:
            is_finite = False
        
        if not is_finite:
            raise ValueError("cost must be a finite number")
        
        if cost < 0:
            raise ValueError("cost must not be negative")
        
        # Accrue tokens based on elapsed time
        if prev_timestamp is None:
            elapsed = 0
        else:
            elapsed = timestamp - prev_timestamp
        tokens = min(capacity, tokens + elapsed * refill_per_second)
        prev_timestamp = timestamp
        
        # Decide admission with floating-point slack
        if tokens + 1e-9 >= cost:
            results.append(True)
            tokens = max(0.0, tokens - cost)
        else:
            results.append(False)
    
    return results
