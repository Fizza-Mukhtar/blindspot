import math

def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Returns a list of delays in seconds for exponential backoff with full jitter,
    following the AWS Architecture Blog formula: delay = rand(min(cap, base * 2**i)).
    """
    # Validate attempts first
    if attempts < 0:
        raise ValueError("attempts")
    
    if attempts == 0:
        return []
    
    # Validate base
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base")
    
    # Validate cap
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap")
    
    delays = []
    ceiling = base  # Start with base * 2**0 = base
    
    for _ in range(attempts):
        # Actual ceiling is clamped to cap
        actual_ceiling = min(ceiling, cap)
        
        # Get delay from rand with this ceiling
        delay = rand(actual_ceiling)
        delays.append(delay)
        
        # Double ceiling for next iteration, unless we've reached the cap
        if ceiling < cap:
            ceiling *= 2
    
    return delays
