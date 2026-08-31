import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """Determine whether a user falls within a flag's percentage rollout.

    Uses a stable SHA-256-based bucketing scheme over ``(flag_key, user_id)``
    so that the result is consistent across processes, languages, and ramp
    steps, and widening ``percentage`` only ever adds users, never removes
    them.
    """
    if not isinstance(flag_key, str):
        raise TypeError("flag_key must be a str")
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a str")
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError("percentage must be an int")
    if not 0 <= percentage <= 100:
        raise ValueError("percentage must be between 0 and 100 inclusive")

    material = f"{flag_key}:{user_id}".encode("utf-8")
    bucket = int(hashlib.sha256(material).hexdigest(), 16) % 100
    return bool(bucket < percentage)
