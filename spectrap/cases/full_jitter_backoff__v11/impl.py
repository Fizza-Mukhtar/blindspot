import math

def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """Compute a Full Jitter retry schedule."""
    
    # Validate in order
    if attempts < 0:
        raise ValueError("attempts")
    
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base")
    
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap")
    
    result = []
    uncapped_ceiling = base
    hit_cap = False
    
    for i in range(attempts):
        if not hit_cap:
            if uncapped_ceiling >= cap:
                hit_cap = True
                ceiling = cap
            else:
                ceiling = uncapped_ceiling
                uncapped_ceiling = uncapped_ceiling * 2
        else:
            ceiling = cap
        
        delay = rand(ceiling)
        result.append(delay)
    
    return result
