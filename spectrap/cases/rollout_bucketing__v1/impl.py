import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """Deterministically decide whether a user is inside a flag's rollout percentage.

    Buckets a (flag_key, user_id) pair into one of 100 buckets via SHA-256,
    independent of percentage, so widening the rollout only ever adds users.
    """
    if not isinstance(flag_key, str) or not isinstance(user_id, str):
        raise TypeError("flag_key and user_id must be str")
    if not isinstance(percentage, int) or isinstance(percentage, bool):
        raise TypeError("percentage must be an int")
    if not 0 <= percentage <= 100:
        raise ValueError("percentage must be between 0 and 100 inclusive")

    material = f"{flag_key}:{user_id}".encode("utf-8")
    bucket = int(hashlib.sha256(material).hexdigest(), 16) % 100
    return bool(bucket < percentage)
