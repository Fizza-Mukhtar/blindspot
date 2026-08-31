def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """
    Allocate an amount across weighted payees using largest-remainder apportionment.
    
    Ensures sum(result) == total_cents exactly, handling fractional remainders
    without losing a cent to rounding.
    """
    # Validation - happens before any allocation
    if not weights:
        raise ValueError("weights list cannot be empty")
    
    if any(w < 0 for w in weights):
        raise ValueError("weights cannot contain negative values")
    
    weight_sum = sum(weights)
    if weight_sum == 0:
        raise ValueError("not all weights can be zero")
    
    # Handle zero case
    if total_cents == 0:
        return [0] * len(weights)
    
    # Handle negative case
    if total_cents < 0:
        positive_result = allocate(-total_cents, weights)
        return [-x for x in positive_result]
    
    # Positive case - use largest-remainder apportionment
    W = weight_sum
    
    # Step 1: Calculate floor and remainder for each payee's exact claim
    floors = []
    remainders = []
    for i, w in enumerate(weights):
        exact_numerator = total_cents * w
        floor_amount = exact_numerator // W
        remainder = exact_numerator % W
        floors.append(floor_amount)
        remainders.append(remainder)
    
    # Step 2: Calculate how many units were lost to flooring
    sum_floors = sum(floors)
    leftover = total_cents - sum_floors
    
    # Step 3: Distribute leftover units to payees with largest remainders
    # Ties are broken by earliest index
    remainder_with_index = [(remainders[i], i) for i in range(len(weights))]
    remainder_with_index.sort(key=lambda x: (-x[0], x[1]))
    
    # Award one unit to each of the top `leftover` payees by remainder
    for i in range(leftover):
        remainder_value, payee_index = remainder_with_index[i]
        floors[payee_index] += 1
    
    return floors
