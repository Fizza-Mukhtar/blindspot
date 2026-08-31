import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Returns delays for retry attempts using Full Jitter: each delay is rand(min(cap, base * 2**i)).
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
    
    result = []
    ceiling = base
    for i in range(attempts):
        delay = rand(ceiling)
        result.append(delay)
        
        # Update ceiling for next iteration: min(cap, ceiling * 2)
        # This represents min(cap, base * 2**(i+1)) without computing large powers
        if ceiling < cap:
            ceiling = min(cap, ceiling * 2)
    
    return result
