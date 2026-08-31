import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """
    Determines if a user is enabled for a feature flag based on consistent bucketing.
    
    Args:
        flag_key: The feature flag identifier.
        user_id: The user identifier.
        percentage: The rollout percentage (0-100 inclusive).
    
    Returns:
        True if the user is within the rollout percentage, False otherwise.
    
    Raises:
        TypeError: If arguments have incorrect types.
        ValueError: If percentage is outside [0, 100].
    """
    # Type checks (must happen before range checks)
    if not isinstance(flag_key, str):
        raise TypeError(f"flag_key must be str, not {type(flag_key).__name__}")
    if not isinstance(user_id, str):
        raise TypeError(f"user_id must be str, not {type(user_id).__name__}")
    
    # percentage must be int, explicitly not bool
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError(f"percentage must be int, not {type(percentage).__name__}")
    
    # Range check
    if not (0 <= percentage <= 100):
        raise ValueError(f"percentage must be in range [0, 100], not {percentage}")
    
    # Calculate bucket using SHA-256
    material = f"{flag_key}:{user_id}"
    bucket = int(hashlib.sha256(material.encode("utf-8")).hexdigest(), 16) % 100
    
    return bucket < percentage
