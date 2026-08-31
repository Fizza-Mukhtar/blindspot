def allocate(total_cents: int, weights: list[int]) -> list[int]:
    """Split total_cents across weighted payees using largest-remainder
    (Hamilton) apportionment, exact in integer arithmetic.

    Guarantees sum(result) == total_cents for every accepted input.
    Ties in fractional remainder are broken by lowest index first.
    Negative totals are handled by allocating the magnitude and negating.
    """
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0 for w in weights):
        raise ValueError("weights must not contain negative values")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must contain at least one positive value")

    sign = -1 if total_cents < 0 else 1
    amount = abs(total_cents)

    floors: list[int] = []
    remainders: list[int] = []
    for w in weights:
        share, remainder = divmod(amount * w, total_weight)
        floors.append(share)
        remainders.append(remainder)

    leftover = amount - sum(floors)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))

    result = list(floors)
    for i in order[:leftover]:
        result[i] += 1

    return [sign * x for x in result]
