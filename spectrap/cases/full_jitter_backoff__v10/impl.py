"""Full Jitter retry schedule computation."""

import math
from typing import Callable


def schedule(attempts: int, base: float, cap: float, rand: Callable[[float], float]) -> list[float]:
    """
    Compute a Full Jitter retry schedule.
    
    Returns a list of delays (in seconds) for each retry attempt.
    Element i is the delay to wait before retry attempt i (0-indexed).
    Each delay is computed as rand(ceiling_i) where ceiling_i = min(cap, base * 2**i).
    
    Args:
        attempts: Number of retry attempts (must be >= 0)
        base: Base delay multiplier (must be finite and > 0)
        cap: Maximum ceiling value (must be finite and > 0)
        rand: Function that returns a random float in [0, upper] given upper
    
    Returns:
        List of delays, one per attempt
    
    Raises:
        ValueError: If attempts < 0, or if base/cap are not finite and positive
    """
    # Validate in order: attempts, base, cap
    if attempts < 0:
        raise ValueError("attempts")
    
    if not _is_finite_positive(base):
        raise ValueError("base")
    
    if not _is_finite_positive(cap):
        raise ValueError("cap")
    
    if attempts == 0:
        return []
    
    result = []
    ceiling = base  # Start with base * 2**0
    reached_cap = False
    
    for _ in range(attempts):
        # ceiling is currently base * 2**i for iteration i
        actual_ceiling = min(cap, ceiling)
        delay = rand(actual_ceiling)
        result.append(delay)
        
        # For the next iteration, double ceiling for base * 2**(i+1)
        if not reached_cap:
            ceiling *= 2
            if ceiling >= cap:
                reached_cap = True
                ceiling = cap  # Optimize: once we reach cap, keep it at cap
    
    return result


def _is_finite_positive(x: float) -> bool:
    """Check if x is a finite number strictly greater than zero."""
    return math.isfinite(x) and x > 0
