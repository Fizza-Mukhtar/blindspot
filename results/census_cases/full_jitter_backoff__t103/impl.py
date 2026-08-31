import math

def _validate_inputs(attempts: int, base: float, cap: float) -> None:
    if attempts < 0:
        raise ValueError("attempts: must be >= 0")
    if not math.isfinite(base) or base <= 0:
        raise ValueError("base: must be finite and > 0")
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("cap: must be finite and > 0")

def _compute_delays(attempts: int, base: float, cap: float, rand) -> list[float]:
    delays = []
    current = base
    
    for _ in range(attempts):
        ceiling = min(cap, current)
        delay = rand(ceiling)
        delays.append(delay)
        
        if current < cap:
            current = current * 2
        else:
            current = cap
    
    return delays

def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """Compute a Full Jitter retry schedule."""
    _validate_inputs(attempts, base, cap)
    return _compute_delays(attempts, base, cap, rand)
