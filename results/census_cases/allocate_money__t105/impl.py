def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Allocate total_cents across weighted payees using largest-remainder method.
    
    Returns a list of integers summing to total_cents, distributed according to weights.
    Uses the Hamilton apportionment method to ensure exact allocation without loss.
    """
    # Validate inputs
    if not weights:
        raise ValueError("weights cannot be empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("all weights must be non-negative")
    
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("at least one weight must be non-zero")
    
    # Handle zero total
    if total_cents == 0:
        return [0] * len(weights)
    
    # Factor out sign
    sign = 1 if total_cents >= 0 else -1
    abs_total = abs(total_cents)
    
    # Compute floors and remainders using integer arithmetic
    floors = []
    remainders = []
    for weight in weights:
        quotient, remainder = divmod(abs_total * weight, total_weight)
        floors.append(quotient)
        remainders.append(remainder)
    
    # Calculate leftover
    leftover = abs_total - sum(floors)
    
    # Distribute leftover to payees with largest remainders
    # Create list of (remainder, index) and sort
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    # Sort by remainder descending, then by index ascending (for tie-breaking)
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Give one unit to the top `leftover` payees
    for i in range(leftover):
        idx = remainder_with_index[i][1]
        floors[idx] += 1
    
    # Apply sign
    result = [sign * f for f in floors]
    return result
