def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Allocate an amount across weighted payees without rounding loss.
    
    Uses the largest-remainder (Hamilton) apportionment method to ensure
    the sum of allocated amounts equals the total exactly.
    
    Args:
        total_cents: Amount in minor units (e.g., cents)
        weights: Relative claim weights for each payee
    
    Returns:
        List of allocated amounts, same length as weights
    
    Raises:
        ValueError: If weights is empty, contains negative values, or all zeros
    """
    # Validation
    if not weights:
        raise ValueError("weights list cannot be empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("all weights must be non-negative")
    
    if sum(weights) == 0:
        raise ValueError("at least one weight must be positive")
    
    # Handle zero total
    if total_cents == 0:
        return [0] * len(weights)
    
    # Factor out sign for negative amounts
    if total_cents < 0:
        return [-x for x in allocate(-total_cents, weights)]
    
    # Compute allocation using largest-remainder method
    W = sum(weights)
    
    # Calculate floors and remainders using integer division
    floors = []
    remainders = []
    for w in weights:
        quotient, remainder = divmod(total_cents * w, W)
        floors.append(quotient)
        remainders.append(remainder)
    
    # Calculate how much is left to distribute
    leftover = total_cents - sum(floors)
    
    # Sort indices by remainder (descending), then by index (ascending for ties)
    sorted_indices = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    
    # Distribute remaining units to payees with largest remainders
    allocation = floors[:]
    for i in range(leftover):
        index = sorted_indices[i]
        allocation[index] += 1
    
    return allocation
