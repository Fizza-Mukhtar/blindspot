import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """
    Determine if a user is enabled for a feature flag based on consistent bucketing.
    
    Each (flag_key, user_id) pair is assigned to a bucket (0-99) based on SHA-256 hash.
    The user is enabled if their bucket is strictly less than the percentage.
    
    Args:
        flag_key: The feature flag identifier (must be str)
        user_id: The user identifier (must be str)
        percentage: The rollout percentage (must be int in range [0, 100])
    
    Returns:
        True if the user is enabled for this flag at this percentage, False otherwise
    
    Raises:
        TypeError: If flag_key or user_id is not a str, or if percentage is not an int
        ValueError: If percentage is not in the range [0, 100]
    """
    # Type checks first
    if not isinstance(flag_key, str):
        raise TypeError(f"flag_key must be str, not {type(flag_key).__name__}")
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be str, not {type(user_id).__name__}")
    
    # Check percentage is int (not bool, not float)
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError(f"percentage must be int, not {type(percentage).__name__}")
    
    # Range check for percentage
    if not (0 <= percentage <= 100):
        raise ValueError(f"percentage must be in range [0, 100], not {percentage}")
    
    # Compute bucket
    material = f"{flag_key}:{user_id}"
    bucket = int(hashlib.sha256(material.encode("utf-8")).hexdigest(), 16) % 100
    
    # User is enabled if bucket < percentage
    return bucket < percentage
