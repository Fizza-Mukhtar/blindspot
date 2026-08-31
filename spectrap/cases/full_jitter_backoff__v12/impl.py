import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Returns a list of delays in seconds for each retry attempt.
    """
    # Validate attempts first
    if attempts < 0:
        raise ValueError("attempts")
    
    # Handle empty case
    if attempts == 0:
        return []
    
    # Validate base
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base")
    
    # Validate cap
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap")
    
    result = []
    ceiling = base
    
    for _ in range(attempts):
        # Apply cap to current ceiling
        actual_ceiling = min(cap, ceiling)
        
        # Draw delay from uniform distribution [0, actual_ceiling]
        delay = rand(actual_ceiling)
        result.append(delay)
        
        # Update ceiling for next iteration (double it)
        # But only if we haven't hit the cap yet
        if actual_ceiling < cap:
            ceiling = ceiling * 2
    
    return result
