def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Allocate a total amount across weighted payees using the largest-remainder method.
    
    Uses integer arithmetic to ensure the sum of allocated amounts exactly equals
    the input total, even when the weights do not divide evenly.
    
    Args:
        total_cents: Amount in minor units (can be negative for refunds/chargebacks)
        weights: List of relative weights for each payee
    
    Returns:
        List of allocated amounts, same length as weights, summing to total_cents
    
    Raises:
        ValueError: If weights is empty, contains negative values, or is all zeros
    """
    # Validation
    if not weights:
        raise ValueError("weights cannot be empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("weights cannot contain negative values")
    
    if all(w == 0 for w in weights):
        raise ValueError("weights cannot all be zero")
    
    # Handle zero total
    if total_cents == 0:
        return [0] * len(weights)
    
    # Handle negative total: allocate absolute value and negate
    if total_cents < 0:
        result = allocate(-total_cents, weights)
        return [-x for x in result]
    
    # Allocate positive total_cents
    return _allocate_positive(total_cents, weights)


def _allocate_positive(total_cents: int, weights: list[int]) -> list[int]:
    """Helper to allocate a positive amount using largest-remainder method."""
    W = sum(weights)
    
    # Calculate floors and remainders for each payee's exact claim
    floors = []
    remainders = []
    total_floor = 0
    
    for w in weights:
        quotient, remainder = divmod(total_cents * w, W)
        floors.append(quotient)
        remainders.append(remainder)
        total_floor += quotient
    
    # Calculate how many units remain to be distributed
    leftover = total_cents - total_floor
    
    # Distribute remaining units to payees with largest remainders,
    # breaking ties by earlier index
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Award one extra unit to each of the top 'leftover' payees
    result = floors[:]
    for i in range(leftover):
        idx = remainder_with_index[i][1]
        result[idx] += 1
    
    return result
