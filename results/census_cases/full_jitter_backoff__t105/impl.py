import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.

    Returns a list of `attempts` delays in seconds, where element i is the wait
    before retry attempt i. Uses the Full Jitter formula from AWS Architecture Blog.

    Args:
        attempts: Number of retry delays to compute (non-negative integer)
        base: Base delay in seconds (finite, strictly positive)
        cap: Maximum delay in seconds (finite, strictly positive)
        rand: Callable that takes an upper bound and returns a float in [0, upper]

    Returns:
        List of delays in seconds

    Raises:
        ValueError: If attempts < 0, or if base/cap are not finite or <= 0
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
    current_ceiling = base

    for i in range(attempts):
        # Ceiling is min(cap, base * 2**i)
        ceiling = min(current_ceiling, cap)

        # Call rand with the ceiling
        delay = rand(ceiling)
        delays.append(delay)

        # Prepare for next iteration by doubling the ceiling
        # (unless we've already reached the cap)
        if current_ceiling < cap:
            current_ceiling *= 2

    return delays
