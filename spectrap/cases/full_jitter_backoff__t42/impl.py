import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Args:
        attempts: Number of retry attempts (non-negative integer)
        base: Base delay in seconds (finite, positive)
        cap: Maximum delay in seconds (finite, positive)
        rand: Callable that takes an upper bound and returns a float in [0, upper]
    
    Returns:
        List of delay times in seconds for each retry attempt
    
    Raises:
        ValueError: If attempts < 0, or if base/cap are not finite and positive
    """
    # Validate attempts
    if attempts < 0:
        raise ValueError("attempts must be non-negative")
    
    # Validate base
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base must be finite and positive")
    
    # Validate cap
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap must be finite and positive")
    
    delays = []
    power_of_2 = 1
    
    for _ in range(attempts):
        exponential = base * power_of_2
        ceiling = min(cap, exponential)
        delay = rand(ceiling)
        delays.append(delay)
        
        # Stop incrementing exponent once we've capped to avoid huge 2^i values
        if exponential < cap:
            power_of_2 *= 2
    
    return delays
