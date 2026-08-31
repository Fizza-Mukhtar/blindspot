import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """Compute a Full Jitter retry schedule.
    
    Returns a list of delays in seconds, one per retry attempt, using the
    Full Jitter algorithm from AWS Architecture Blog.
    """
    # Validate attempts
    if attempts < 0:
        raise ValueError("attempts: must be non-negative")
    
    # Validate base
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base: must be a positive finite number")
    
    # Validate cap
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap: must be a positive finite number")
    
    # Early return for empty case
    if attempts == 0:
        return []
    
    delays = []
    power_of_two = 1  # 2**0
    
    for i in range(attempts):
        ceiling = base * power_of_two
        
        if ceiling >= cap:
            # Cap reached, use cap for all remaining attempts
            delays.append(rand(cap))
            for j in range(i + 1, attempts):
                delays.append(rand(cap))
            break
        else:
            delays.append(rand(ceiling))
        
        power_of_two *= 2  # Prepare for next iteration
    
    return delays
