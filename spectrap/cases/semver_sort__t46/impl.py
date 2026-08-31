def sort_versions(tags: list[str]) -> list[str]:
    """Sort git tags by Semantic Versioning precedence (lowest first)."""
    
    def parse_version(tag):
        """Parse a tag and return (major, minor, patch, prerelease)."""
        original_tag = tag
        
        # Remove leading 'v' if present
        if tag.startswith('v'):
            tag = tag[1:]
        
        # Split by '+' to separate build metadata (which we ignore for ordering)
        if '+' in tag:
            tag = tag.split('+', 1)[0]
        
        # Split by '-' to separate pre-release
        if '-' in tag:
            core_part, prerelease_str = tag.split('-', 1)
        else:
            core_part = tag
            prerelease_str = None
        
        # Parse core version
        parts = core_part.split('.')
        if len(parts) != 3:
            raise ValueError(original_tag)
        
        major_str, minor_str, patch_str = parts
        
        # Validate each part
        for part in [major_str, minor_str, patch_str]:
            if not part or not part.isdigit():
                raise ValueError(original_tag)
            if len(part) > 1 and part[0] == '0':
                raise ValueError(original_tag)
        
        major = int(major_str)
        minor = int(minor_str)
        patch = int(patch_str)
        
        # Parse pre-release if present
        prerelease = None
        if prerelease_str:
            prerelease = prerelease_str.split('.')
            
            # Validate pre-release identifiers
            for identifier in prerelease:
                if not identifier:
                    raise ValueError(original_tag)
                # Check for leading zeroes on numeric identifiers
                if identifier.isdigit() and len(identifier) > 1 and identifier[0] == '0':
                    raise ValueError(original_tag)
        
        return (major, minor, patch, prerelease)
    
    class VersionKey:
        """Comparable version key for sorting."""
        def __init__(self, tag):
            self.tag = tag
            self.major, self.minor, self.patch, self.prerelease = parse_version(tag)
        
        def __lt__(self, other):
            # Compare core version
            if self.major != other.major:
                return self.major < other.major
            if self.minor != other.minor:
                return self.minor < other.minor
            if self.patch != other.patch:
                return self.patch < other.patch
            
            # Compare pre-release
            pre1 = self.prerelease
            pre2 = other.prerelease
            
            # No pre-release means higher precedence
            if pre1 is None and pre2 is None:
                return False
            if pre1 is None:  # self has higher precedence
                return False
            if pre2 is None:  # other has higher precedence
                return True
            
            # Both have pre-release, compare identifiers
            for i in range(min(len(pre1), len(pre2))):
                id1 = pre1[i]
                id2 = pre2[i]
                
                is_num1 = id1.isdigit()
                is_num2 = id2.isdigit()
                
                if is_num1 and is_num2:
                    # Both numeric, compare as integers
                    n1 = int(id1)
                    n2 = int(id2)
                    if n1 < n2:
                        return True
                    if n1 > n2:
                        return False
                elif is_num1:
                    # Numeric identifiers have lower precedence than non-numeric
                    return True
                elif is_num2:
                    # Non-numeric has higher precedence than numeric
                    return False
                else:
                    # Both non-numeric, compare lexically
                    if id1 < id2:
                        return True
                    if id1 > id2:
                        return False
            
            # All compared identifiers are equal
            return len(pre1) < len(pre2)
    
    # Create version keys
    keys = [VersionKey(tag) for tag in tags]
    
    # Sort keys (stable sort maintains order for equal elements)
    sorted_keys = sorted(keys)
    
    # Extract tags from sorted keys
    return [key.tag for key in sorted_keys]
