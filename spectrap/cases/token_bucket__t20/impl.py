import math


def simulate(
    capacity: float,
    refill_per_second: float,
    requests: list[tuple[float, float]],
) -> list[bool]:
    """
    Simulate a token bucket rate limiter over a recorded request trace.
    
    Implements a classic token bucket with continuous credit accrual.
    Returns a list of decisions (True for admitted, False for rejected)
    for each request in the trace.
    """
    # Validate capacity
    if not (isinstance(capacity, (int, float)) and math.isfinite(capacity) and capacity > 0):
        raise ValueError("capacity must be a finite number greater than zero")
    
    # Validate refill_per_second
    if not (isinstance(refill_per_second, (int, float)) and math.isfinite(refill_per_second) and refill_per_second > 0):
        raise ValueError("refill_per_second must be a finite number greater than zero")
    
    # Handle empty trace
    if not requests:
        return []
    
    # Validate requests and check timestamp order
    last_timestamp = None
    for timestamp, cost in requests:
        # Validate timestamp
        if not (isinstance(timestamp, (int, float)) and math.isfinite(timestamp)):
            raise ValueError("timestamp must be a finite number")
        
        # Check timestamp order
        if last_timestamp is not None and timestamp < last_timestamp:
            raise ValueError("timestamps must be non-decreasing")
        last_timestamp = timestamp
        
        # Validate cost
        if not (isinstance(cost, (int, float)) and math.isfinite(cost) and cost >= 0):
            raise ValueError("cost must be a finite number and non-negative")
    
    # Initialize token count to capacity and mark to first timestamp
    tokens = float(capacity)
    mark = requests[0][0]
    
    decisions = []
    
    for timestamp, cost in requests:
        # Accrue tokens based on elapsed time
        elapsed = timestamp - mark
        tokens = min(capacity, tokens + elapsed * refill_per_second)
        mark = timestamp
        
        # Decide on admission
        admitted = tokens + 1e-9 >= cost
        decisions.append(admitted)
        
        # If admitted, consume tokens
        if admitted:
            tokens = max(0.0, tokens - cost)
    
    return decisions
