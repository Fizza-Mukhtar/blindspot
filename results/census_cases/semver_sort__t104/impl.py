def sort_versions(tags: list[str]) -> list[str]:
    """
    Sort git version tags by Semantic Versioning 2.0.0 precedence.
    
    Returns a new list sorted from lowest to highest precedence, maintaining
    original order for tags with equal precedence.
    
    Raises ValueError if any tag is malformed.
    """
    if not tags:
        return []
    
    parsed = []
    for i, tag in enumerate(tags):
        version = _parse_version(tag)
        parsed.append((version, i, tag))
    
    # Sort by version, using index to maintain order for equal versions
    sorted_parsed = sorted(parsed, key=lambda x: (x[0], x[1]))
    
    return [tag for _, _, tag in sorted_parsed]


def _parse_version(tag: str) -> tuple:
    """
    Parse a semantic version tag and return a comparison key.
    
    Raises ValueError if the tag is malformed.
    """
    original = tag
    
    # Remove leading 'v' if present
    if tag.startswith('v'):
        tag = tag[1:]
    
    # Split by '+' to remove build metadata
    if '+' in tag:
        tag = tag.split('+')[0]
    
    # Split by '-' to separate prerelease
    if '-' in tag:
        version_part, prerelease_part = tag.split('-', 1)
    else:
        version_part = tag
        prerelease_part = None
    
    # Parse version numbers
    parts = version_part.split('.')
    if len(parts) != 3:
        raise ValueError(original)
    
    # Try to parse as integers
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        raise ValueError(original)
    
    major, minor, patch = nums
    
    # Validate no leading zeroes
    for part in parts:
        if len(part) > 1 and part[0] == '0':
            raise ValueError(original)
    
    # Parse prerelease
    if prerelease_part is not None:
        if not prerelease_part:
            raise ValueError(original)
        prerelease_key = _parse_prerelease(prerelease_part, original)
        # Versions with prerelease have lower precedence
        precedence_key = (0, prerelease_key)
    else:
        # Versions without prerelease have higher precedence
        precedence_key = (1,)
    
    return (major, minor, patch, precedence_key)


def _parse_prerelease(prerelease_str: str, original_tag: str) -> tuple:
    """
    Parse prerelease identifiers and return a comparison key.
    
    Raises ValueError if the prerelease is malformed.
    """
    identifiers = prerelease_str.split('.')
    
    # Check for empty identifiers
    if any(not ident for ident in identifiers):
        raise ValueError(original_tag)
    
    keys = []
    for ident in identifiers:
        if ident.isdigit():
            # Numeric identifier
            if len(ident) > 1 and ident[0] == '0':
                # Leading zero not allowed
                raise ValueError(original_tag)
            # Use (0, int_value) so numeric < alphanumeric
            keys.append((0, int(ident)))
        else:
            # Alphanumeric identifier
            # Use (1, string) so numeric < alphanumeric
            keys.append((1, ident))
    
    return tuple(keys)
