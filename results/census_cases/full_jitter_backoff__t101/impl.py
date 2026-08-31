import math

def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """Compute a Full Jitter retry schedule.
    
    Returns a list of `attempts` delays in seconds, element i the wait before
    retry attempt i. Uses the Full Jitter formula from AWS Architecture Blog:
    sleep = random_between(0, min(cap, base * 2 ** attempt)).
    
    Args:
        attempts: Number of retry attempts. Must be >= 0.
        base: Base delay in seconds. Must be finite and > 0.
        cap: Maximum delay in seconds. Must be finite and > 0.
        rand: A callable that returns a random float in [0, upper] given upper.
    
    Returns:
        A list of float delays in seconds.
    
    Raises:
        ValueError: If attempts, base, or cap are invalid.
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
    power_of_two = 1.0
    
    for i in range(attempts):
        ceiling = min(cap, base * power_of_two)
        delay = rand(ceiling)
        result.append(delay)
        
        # Only keep doubling if we haven't hit the cap yet
        if ceiling < cap:
            power_of_two *= 2
    
    return result
