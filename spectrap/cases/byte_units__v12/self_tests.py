import impl
import pytest

# ============================================================================
# Basic Cases and Bytes Unit
# ============================================================================

def test_zero():
    """Zero outputs '0 B' regardless of mode."""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"

def test_bytes_under_divisor():
    """Values below the divisor show as bytes with no decimal point."""
    # SI: values < 1000
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"
    # IEC: values < 1024
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"

# ============================================================================
# Unit Progression - SI (powers of 1000)
# ============================================================================

def test_unit_progression_si():
    """SI units progress correctly: B, kB, MB, GB, TB, PB."""
    assert impl.format_bytes(1000) == "1.0 kB"  # lowercase k
    assert impl.format_bytes(1_000_000) == "1.0 MB"
    assert impl.format_bytes(1_000_000_000) == "1.0 GB"
    assert impl.format_bytes(1_000_000_000_000) == "1.0 TB"
    assert impl.format_bytes(1_000_000_000_000_000) == "1.0 PB"

# ============================================================================
# Unit Progression - IEC (powers of 1024)
# ============================================================================

def test_unit_progression_iec():
    """IEC units progress correctly: B, KiB, MiB, GiB, TiB, PiB."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"  # uppercase K
    assert impl.format_bytes(1_048_576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1_073_741_824, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1_099_511_627_776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1_125_899_906_842_624, binary=True) == "1.0 PiB"

# ============================================================================
# Round Half Up and Promotion
# ============================================================================

def test_round_half_up_behavior():
    """Verify round half up: 1150 bytes = 1.15 kB rounds to 1.2 kB (SI)."""
    assert impl.format_bytes(1150) == "1.2 kB"
    assert impl.format_bytes(1149) == "1.1 kB"
    # IEC: 1150 bytes = 1.123... KiB rounds to 1.1 KiB
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"

def test_promotion_after_rounding():
    """Rounding can promote to the next unit if result >= divisor."""
    # SI: 999950 = 999.95 kB rounds to 1000.0 kB, must promote to 1.0 MB
    assert impl.format_bytes(999_950) == "1.0 MB"
    # IEC: 1048575 = 1023.999... KiB rounds to 1024.0 KiB, must promote to 1.0 MiB
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"
    # SI: 1048575 = 1048.575 kB rounds to 1048.6 kB, promotes to 1.0 MB
    assert impl.format_bytes(1_048_575) == "1.0 MB"
    # No promotion: 999949 = 999.949 kB rounds to 999.9 kB (stays as kB)
    assert impl.format_bytes(999_949) == "999.9 kB"

# ============================================================================
# Negative Values
# ============================================================================

def test_negative_values():
    """Negative values get a leading minus sign."""
    assert impl.format_bytes(-999) == "-999 B"
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1_000_000) == "-1.0 MB"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"

# ============================================================================
# Very Large Values
# ============================================================================

def test_very_large_values():
    """Values above PB/PiB stay in the top unit; integer part is uncapped."""
    # 1500 PB in SI mode
    assert impl.format_bytes(1_500_000_000_000_000_000) == "1500.0 PB"
    # 2^60 bytes in IEC mode (larger than any exact unit)
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"

# ============================================================================
# Type Errors
# ============================================================================

def test_type_errors():
    """Only int (not bool) is accepted; everything else raises TypeError."""
    # Float, even whole-valued
    with pytest.raises(TypeError):
        impl.format_bytes(1.0)
    # bool is a subclass of int, but we reject it
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)
    # Other types
    with pytest.raises(TypeError):
        impl.format_bytes("100")
    with pytest.raises(TypeError):
        impl.format_bytes(None)

# ============================================================================
# Formatting and Specification Details
# ============================================================================

def test_formatting_details():
    """Verify formatting: exactly one decimal, one space, no separators."""
    result = impl.format_bytes(1000)
    assert result == "1.0 kB"  # exactly one decimal
    parts = result.split(' ')
    assert len(parts) == 2  # exactly one space
    assert ',' not in result  # no thousands separators
    
    # Large number check
    result_large = impl.format_bytes(1_500_000)
    assert result_large == "1.5 MB"
    assert ',' not in result_large

# ============================================================================
# Comprehensive Specification Examples
# ============================================================================

def test_specification_examples():
    """All examples from the ticket specification."""
    # Basic cases
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1024) == "1.0 kB"
    
    # IEC comparison at same values
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    
    # Rounding differences between SI and IEC
    assert impl.format_bytes(1150) == "1.2 kB"
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"
    
    # Detailed IEC example
    assert impl.format_bytes(999_949, binary=True) == "976.5 KiB"
    
    # Promotion examples
    assert impl.format_bytes(999_950) == "1.0 MB"
    assert impl.format_bytes(1_048_575) == "1.0 MB"
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"
    
    # Negative
    assert impl.format_bytes(-1500) == "-1.5 kB"
