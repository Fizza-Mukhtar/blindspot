def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """Split total_cents across payees in proportion to weights.

    Implements Fowler's Money.allocate / largest-remainder apportionment:
    each payee gets the floor of its exact rational share, and any leftover
    minor units go one each to the payees with the largest fractional
    remainders (ties broken by lowest index first). The result always sums
    exactly to total_cents, for positive, negative, and zero amounts.

    Raises:
        ValueError: if weights is empty, contains a negative value, or is
            all zeros.
    """
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must not contain negative values")

    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must contain at least one non-zero value")

    sign = -1 if total_cents < 0 else 1
    magnitude = abs(total_cents)

    floors = [0] * len(weights)
    remainders = [0] * len(weights)
    for i, weight in enumerate(weights):
        floors[i], remainders[i] = divmod(magnitude * weight, total_weight)

    leftover = magnitude - sum(floors)

    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        floors[i] += 1

    return [sign * amount for amount in floors]
