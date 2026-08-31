def sort_versions(tags: list[str]) -> list[str]:
    """Sort version tags according to Semantic Versioning 2.0.0 precedence.
    
    Returns a new list sorted by version precedence (lowest first), preserving
    original tag strings. Tags that tie are kept in input order.
    
    Raises ValueError if any tag is malformed per Semantic Versioning 2.0.0.
    """
    
    def parse_and_validate(tag: str) -> tuple:
        """Parse a tag and return a sort key for precedence comparison."""
        original_tag = tag
        
        # Remove leading 'v' if present
        if tag.startswith('v'):
            tag = tag[1:]
        
        # Split off build metadata (after +)
        # Build metadata is ignored for version precedence
        if '+' in tag:
            tag = tag.split('+', 1)[0]
        
        # Split off pre-release (after -)
        prerelease_str = None
        if '-' in tag:
            tag, prerelease_str = tag.split('-', 1)
        
        # Parse MAJOR.MINOR.PATCH
        parts = tag.split('.')
        if len(parts) != 3:
            raise ValueError(original_tag)
        
        # Parse and validate core version numbers
        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError:
            raise ValueError(original_tag)
        
        # Check for leading zeroes on core numbers
        for part in parts:
            if part != '0' and part.startswith('0'):
                raise ValueError(original_tag)
        
        # Parse pre-release identifiers
        if prerelease_str is not None:
            identifiers = prerelease_str.split('.')
            
            # Check for empty identifiers
            if not identifiers or any(not ident for ident in identifiers):
                raise ValueError(original_tag)
            
            prerelease_parts = []
            for identifier in identifiers:
                if identifier.isdigit():
                    # Check for leading zeroes on numeric identifiers
                    if identifier != '0' and identifier.startswith('0'):
                        raise ValueError(original_tag)
                    prerelease_parts.append((0, int(identifier)))
                else:
                    # Non-numeric identifier
                    prerelease_parts.append((1, identifier))
            
            prerelease_sort_key = (0, tuple(prerelease_parts))
        else:
            # No pre-release: sorts after all pre-releases
            prerelease_sort_key = (1, ())
        
        return (major, minor, patch, prerelease_sort_key)
    
    # Parse all tags and build sort keys
    sort_keys_and_tags = []
    for tag in tags:
        sort_key = parse_and_validate(tag)
        sort_keys_and_tags.append((sort_key, tag))
    
    # Sort by sort key (Python's sort is stable, so ties preserve input order)
    sort_keys_and_tags.sort(key=lambda x: x[0])
    
    # Return just the original tags in sorted order
    return [tag for _, tag in sort_keys_and_tags]
