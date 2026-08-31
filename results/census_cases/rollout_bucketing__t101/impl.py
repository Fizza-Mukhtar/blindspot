import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """
    Determine if a user is enabled for a feature flag at the given percentage rollout.
    
    Returns True when the (flag_key, user_id) pair falls into a bucket less than
    the percentage threshold (0-100).
    
    Args:
        flag_key: The feature flag identifier (str).
        user_id: The user identifier (str).
        percentage: The rollout percentage (int, 0-100).
    
    Returns:
        bool: True if the user is enabled for this flag.
    
    Raises:
        TypeError: If flag_key or user_id are not str, or if percentage is not int.
        ValueError: If percentage is not in the range [0, 100].
    """
    # Type checking (before range)
    if not isinstance(flag_key, str):
        raise TypeError(f"flag_key must be str, not {type(flag_key).__name__}")
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be str, not {type(user_id).__name__}")
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError(f"percentage must be int, not {type(percentage).__name__}")
    
    # Range checking
    if not (0 <= percentage <= 100):
        raise ValueError(f"percentage must be between 0 and 100, not {percentage}")
    
    # Calculate bucket
    material = f"{flag_key}:{user_id}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    bucket = int(digest, 16) % 100
    
    return bucket < percentage
