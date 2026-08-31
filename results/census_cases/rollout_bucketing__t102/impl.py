import hashlib


def is_enabled(flag_key: str, user_id: str, percentage: int) -> bool:
    """
    Determine if a user is enabled for a feature flag at the given percentage rollout.
    
    Uses consistent bucketing based on SHA-256 hash of flag_key and user_id
    to ensure the same user always gets the same assignment across processes.
    
    Args:
        flag_key: The feature flag identifier
        user_id: The user identifier
        percentage: The rollout percentage (0-100 inclusive)
    
    Returns:
        True if the user is in the rollout, False otherwise
    
    Raises:
        TypeError: If flag_key or user_id are not strings, or if percentage is not an int
        ValueError: If percentage is not in the range [0, 100]
    """
    # Type checking: flag_key must be a string
    if not isinstance(flag_key, str):
        raise TypeError("flag_key must be a str")
    
    # Type checking: user_id must be a string
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a str")
    
    # Type checking: percentage must be an int (not bool, not float)
    # In Python, bool is a subclass of int, so we must check it explicitly
    if isinstance(percentage, bool) or not isinstance(percentage, int):
        raise TypeError("percentage must be an int")
    
    # Range checking: percentage must be 0-100 inclusive
    if not (0 <= percentage <= 100):
        raise ValueError("percentage must be between 0 and 100 inclusive")
    
    # Calculate the bucket for this user
    combined = f"{flag_key}:{user_id}"
    digest_hex = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    bucket = int(digest_hex, 16) % 100
    
    # User is enabled if their bucket is strictly less than the percentage
    return bucket < percentage
