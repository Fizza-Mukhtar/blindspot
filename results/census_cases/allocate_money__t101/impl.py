def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Allocate an amount across weighted payees using largest-remainder apportionment.
    
    Uses integer arithmetic to ensure sum(result) == total_cents exactly.
    """
    # Validation
    if not weights:
        raise ValueError("weights must not be empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("weights must not contain negative values")
    
    W = sum(weights)
    if W == 0:
        raise ValueError("weights must contain at least one positive value")
    
    # Handle zero total
    if total_cents == 0:
        return [0] * len(weights)
    
    # Handle negative by factoring out sign
    if total_cents < 0:
        result = allocate(-total_cents, weights)
        return [-x for x in result]
    
    # Compute floors and remainders
    floors = []
    remainders = []
    total_floor = 0
    
    for w in weights:
        floor, remainder = divmod(total_cents * w, W)
        floors.append(floor)
        remainders.append(remainder)
        total_floor += floor
    
    # Distribute leftover
    leftover = total_cents - total_floor
    
    # Create list of (remainder, index) and sort by remainder desc, then index asc
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Give extra units to the top `leftover` payees
    for i in range(leftover):
        idx = remainder_with_index[i][1]
        floors[idx] += 1
    
    return floors
