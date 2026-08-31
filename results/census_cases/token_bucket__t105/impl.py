import math

def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    """
    Simulate a token bucket rate limiter over a recorded request trace.
    
    Returns a list of admission decisions (True = admitted, False = rejected)
    for each request in the trace, following RFC 2697 semantics with continuous
    accrual.
    """
    # Validate capacity
    if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
        raise ValueError("capacity must be a finite number greater than zero")
    capacity = float(capacity)
    if math.isnan(capacity) or math.isinf(capacity) or capacity <= 0:
        raise ValueError("capacity must be a finite number greater than zero")
    
    # Validate refill_per_second
    if isinstance(refill_per_second, bool) or not isinstance(refill_per_second, (int, float)):
        raise ValueError("refill_per_second must be a finite number greater than zero")
    refill_per_second = float(refill_per_second)
    if math.isnan(refill_per_second) or math.isinf(refill_per_second) or refill_per_second <= 0:
        raise ValueError("refill_per_second must be a finite number greater than zero")
    
    # Empty trace
    if not requests:
        return []
    
    # Validate and process requests
    decisions = []
    tokens = capacity
    mark = None
    prev_timestamp = None
    
    for timestamp, cost in requests:
        # Validate timestamp
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            raise ValueError("timestamp must be a finite number")
        timestamp = float(timestamp)
        if math.isnan(timestamp) or math.isinf(timestamp):
            raise ValueError("timestamp must be a finite number")
        
        # Check non-decreasing
        if prev_timestamp is not None and timestamp < prev_timestamp:
            raise ValueError("timestamps must be non-decreasing")
        
        # Validate cost
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise ValueError("cost must be a non-negative finite number")
        cost = float(cost)
        if math.isnan(cost) or math.isinf(cost) or cost < 0:
            raise ValueError("cost must be a non-negative finite number")
        
        # Initialize mark on first iteration
        if mark is None:
            mark = timestamp
        
        # Accrue tokens
        elapsed = timestamp - mark
        tokens = min(capacity, tokens + elapsed * refill_per_second)
        mark = timestamp
        
        # Admit or reject
        if tokens + 1e-9 >= cost:
            decisions.append(True)
            tokens = max(0.0, tokens - cost)
        else:
            decisions.append(False)
        
        prev_timestamp = timestamp
    
    return decisions
