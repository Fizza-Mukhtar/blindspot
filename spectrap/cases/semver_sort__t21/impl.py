def sort_versions(tags: list[str]) -> list[str]:
    """
    Sort version tags by Semantic Versioning 2.0.0 precedence.
    
    Returns a new sorted list of the same tag strings, lowest precedence first.
    Raises ValueError if any tag is invalid.
    """
    
    def parse_version(tag: str) -> tuple:
        """Parse a version tag and return a comparable tuple."""
        original_tag = tag
        
        # Remove leading 'v' if present
        if tag.startswith('v'):
            tag = tag[1:]
        
        # Split by '+' to separate build metadata (ignored for precedence)
        if '+' in tag:
            tag = tag.split('+', 1)[0]
        
        # Split by '-' to separate pre-release
        if '-' in tag:
            version_part, prerelease = tag.split('-', 1)
        else:
            version_part = tag
            prerelease = None
        
        # Parse version numbers
        parts = version_part.split('.')
        if len(parts) != 3:
            raise ValueError(original_tag)
        
        try:
            major, minor, patch = [int(p) for p in parts]
        except ValueError:
            raise ValueError(original_tag)
        
        # Check for leading zeros in core numbers
        for part in parts:
            if len(part) > 1 and part[0] == '0':
                raise ValueError(original_tag)
        
        # Parse pre-release identifiers
        if prerelease is not None:
            if prerelease == '':
                raise ValueError(original_tag)
            
            identifiers = prerelease.split('.')
            prerelease_tuple = []
            
            for identifier in identifiers:
                if identifier == '':
                    raise ValueError(original_tag)
                
                # Check if identifier is purely numeric
                if identifier.isdigit():
                    # Check for leading zeros
                    if len(identifier) > 1 and identifier[0] == '0':
                        raise ValueError(original_tag)
                    prerelease_tuple.append((0, int(identifier)))
                else:
                    prerelease_tuple.append((1, identifier))
            
            # Return with prerelease: (major, minor, patch, 0, prerelease_tuple)
            return (major, minor, patch, 0, tuple(prerelease_tuple))
        else:
            # No prerelease: (major, minor, patch, 1)
            return (major, minor, patch, 1)
    
    # Parse all versions
    parsed_tags = []
    for tag in tags:
        try:
            parsed = parse_version(tag)
            parsed_tags.append((parsed, tag))
        except ValueError:
            raise ValueError(tag)
    
    # Sort by parsed version (stable sort maintains original order for ties)
    sorted_tags = sorted(parsed_tags, key=lambda x: x[0])
    
    return [tag for _, tag in sorted_tags]
