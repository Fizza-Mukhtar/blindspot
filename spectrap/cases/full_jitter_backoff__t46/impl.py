import math


def schedule(attempts: int, base: float, cap: float, rand) -> list[float]:
    """
    Compute a Full Jitter retry schedule.

    Returns a list of delays in seconds for retry attempts using the Full Jitter
    algorithm from AWS Exponential Backoff And Jitter.

    Args:
        attempts: Number of delays to compute. Must be >= 0.
        base: Base delay in seconds. Must be finite and > 0.
        cap: Maximum delay ceiling in seconds. Must be finite and > 0.
        rand: Callable that returns a float in [0, upper] when called with upper.

    Returns:
        List of delays in seconds, one per attempt.

    Raises:
        ValueError: If attempts < 0, or if base/cap are not finite or <= 0.
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
    power_of_2 = 1  # 2**0 for attempt 0
    cap_ratio = cap / base  # When power_of_2 >= this, ceiling = cap

    for i in range(attempts):
        # Compute ceiling: min(cap, base * power_of_2)
        if power_of_2 >= cap_ratio:
            ceiling = cap
        else:
            ceiling = base * power_of_2

        # Call rand with the ceiling
        delay = rand(ceiling)
        delays.append(delay)

        # Prepare power_of_2 for next attempt, but only if not at cap
        if power_of_2 < cap_ratio:
            power_of_2 *= 2

    return delays
