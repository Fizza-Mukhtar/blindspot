import hashlib

def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """
    Determine if a user is enabled for a feature flag based on consistent bucketing.
    
    Each (flag_key, user_id) pair is deterministically assigned to one of 100
    buckets (0-99) using SHA-256. The user is enabled if their bucket is
    strictly less than the rollout percentage.
    
    Args:
        flag_key: The feature flag identifier.
        user_id: The user identifier.
        percentage: The rollout percentage (0-100 inclusive).
        
    Returns:
        True if the user is in the rollout cohort, False otherwise.
        
    Raises:
        TypeError: If flag_key or user_id is not a str, or if percentage is not
                   an int (including rejection of bool and float).
        ValueError: If percentage is outside 0-100 inclusive.
    """
    # Type checks first (before range checks)
    if not isinstance(flag_key, str):
        raise TypeError(f"flag_key must be str, not {type(flag_key).__name__}")
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be str, not {type(user_id).__name__}")
    
    # Reject bool explicitly since isinstance(True, int) is True
    if isinstance(percentage, bool):
        raise TypeError("percentage must be int, not bool")
    
    if not isinstance(percentage, int):
        raise TypeError(f"percentage must be int, not {type(percentage).__name__}")
    
    # Range check after type checks
    if not (0 <= percentage <= 100):
        raise ValueError(f"percentage must be in range 0-100, got {percentage}")
    
    # Deterministic bucketing using SHA-256
    combined = f"{flag_key}:{user_id}"
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 100
    
    return bucket < percentage
