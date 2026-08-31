import re


def sort_versions(tags: list[str]) -> list[str]:
    """Sort git tags by Semantic Versioning 2.0.0 precedence.
    
    Returns a new list ordered by precedence (lowest first), preserving input
    order for tags with equal precedence.
    
    Raises ValueError for malformed tags.
    """
    
    # Pattern: optional v, then MAJOR.MINOR.PATCH (no leading zeros),
    # optional pre-release after -, optional build after +
    pattern = r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'
    
    parsed = []
    for tag in tags:
        match = re.match(pattern, tag)
        if not match:
            raise ValueError(tag)
        
        major, minor, patch, prerelease, build = match.groups()
        
        # Convert core version numbers to integers
        major = int(major)
        minor = int(minor)
        patch = int(patch)
        
        # Validate and parse pre-release identifiers
        prerelease_parts = None
        if prerelease:
            parts = prerelease.split('.')
            if not all(parts):  # Check for empty identifiers
                raise ValueError(tag)
            prerelease_parts = []
            for part in parts:
                if part.isdigit():
                    # Check for leading zeros on numeric identifiers
                    if len(part) > 1 and part[0] == '0':
                        raise ValueError(tag)
                    prerelease_parts.append((0, int(part)))
                else:
                    prerelease_parts.append((1, part))
        
        # Validate build metadata identifiers
        if build:
            parts = build.split('.')
            if not all(parts):  # Check for empty identifiers
                raise ValueError(tag)
        
        parsed.append((tag, major, minor, patch, prerelease_parts))
    
    # Sort by semantic versioning precedence
    def sort_key(item):
        tag, major, minor, patch, prerelease_parts = item
        # Release versions (no pre-release) have higher precedence
        if prerelease_parts is None:
            prerelease_key = (1,)
        else:
            prerelease_key = (0, prerelease_parts)
        return (major, minor, patch, prerelease_key)
    
    # Stable sort (Python's sorted() is stable by default)
    sorted_parsed = sorted(parsed, key=sort_key)
    
    return [item[0] for item in sorted_parsed]
