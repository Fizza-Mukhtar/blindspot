import math

def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Returns a list of delay times in seconds for retry attempts using the
    Full Jitter formula: sleep = random_between(0, min(cap, base * 2**attempt)).
    
    Args:
        attempts: Number of retry attempts (must be >= 0)
        base: Base delay in seconds (must be finite and > 0)
        cap: Maximum delay in seconds (must be finite and > 0)
        rand: Function that returns a float in [0, upper] when called with upper
    
    Returns:
        List of delays in seconds, one per attempt
        
    Raises:
        ValueError: If validation fails
    """
    # Validate attempts
    if attempts < 0:
        raise ValueError("attempts must be >= 0")
    
    # Validate base
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base must be finite and > 0")
    
    # Validate cap
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap must be finite and > 0")
    
    delays = []
    ceiling = min(cap, base)
    
    for _ in range(attempts):
        delay = rand(ceiling)
        delays.append(delay)
        
        # Update ceiling for next iteration
        if ceiling < cap:
            ceiling = min(cap, ceiling * 2)
    
    return delays
