def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Split total_cents across weighted payees using largest-remainder apportionment.
    
    Returns a list of integers summing to total_cents, allocated proportionally
    to weights using integer arithmetic. Remainders are distributed to payees
    with largest fractional parts, with ties broken by earliest index.
    """
    # Validation
    if not weights:
        raise ValueError("weights list cannot be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights cannot contain negative values")
    if sum(weights) == 0:
        raise ValueError("weights cannot all be zero")
    
    # Handle zero total
    if total_cents == 0:
        return [0] * len(weights)
    
    # Handle negative amounts: allocate positive, then negate
    if total_cents < 0:
        positive_result = allocate(-total_cents, weights)
        return [-x for x in positive_result]
    
    # Positive allocation
    W = sum(weights)
    
    # Compute floors and remainders using integer arithmetic
    floors = []
    remainders = []
    for w in weights:
        quotient, remainder = divmod(total_cents * w, W)
        floors.append(quotient)
        remainders.append(remainder)
    
    # Compute leftover units to distribute
    leftover = total_cents - sum(floors)
    
    # Find indices sorted by remainder (descending), ties broken by index (ascending)
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Award one unit each to the top `leftover` payees
    allocation = floors[:]
    for i in range(leftover):
        idx = remainder_with_index[i][1]
        allocation[idx] += 1
    
    return allocation
