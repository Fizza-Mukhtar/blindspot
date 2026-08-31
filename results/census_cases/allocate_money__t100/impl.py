def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Split a settlement amount across weighted payees using the largest-remainder method.
    
    The sum of returned amounts always equals total_cents, preserving the total to the cent.
    """
    
    # Validation
    if not weights:
        raise ValueError("weights is empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("weights contains negative values")
    
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights are all zero")
    
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
    
    # Calculate leftover units
    leftover = abs_total - sum(floors)
    
    # Distribute leftover to payees with largest remainders
    # Sort by remainder descending, then by index ascending for ties
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Give one unit to the first 'leftover' payees
    for i in range(leftover):
        idx = remainder_with_index[i][1]
        floors[idx] += 1
    
    # Apply sign
    result = [x * sign for x in floors]
    
    return result
