import pytest
import impl

def test_zero():
    """n=0 produces '0 B' in both modes."""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=False) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"

def test_small_bytes_si():
    """Small byte counts below 1000 in SI mode."""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"

def test_small_bytes_binary():
    """Small byte counts below 1024 in binary mode."""
    assert impl.format_bytes(1, binary=True) == "1 B"
    assert impl.format_bytes(999, binary=True) == "999 B"
    assert impl.format_bytes(1000, binary=True) == "1000 B"

def test_kilobyte_si():
    """Test kB unit in SI mode (1000 divisor)."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"

def test_kilobyte_binary():
    """Test KiB unit in binary mode (1024 divisor)."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1536, binary=True) == "1.5 KiB"

def test_rounding_half_up_si():
    """Test round half up behavior in SI mode."""
    assert impl.format_bytes(1150) == "1.2 kB"  # 1.15 rounds up
    assert impl.format_bytes(1149) == "1.1 kB"  # 1.149 rounds down
    assert impl.format_bytes(1145) == "1.1 kB"  # 1.145 rounds down
    assert impl.format_bytes(1144) == "1.1 kB"

def test_rounding_half_up_binary():
    """Test round half up behavior in binary mode."""
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"

def test_promotion_after_rounding_si():
    """Test promotion to next unit after rounding in SI mode."""
    # 999.95 kB rounds to 1000.0 kB, must promote to 1.0 MB
    assert impl.format_bytes(999_950) == "1.0 MB"
    # 999.949 kB rounds to 999.9 kB, no promotion
    assert impl.format_bytes(999_949) == "999.9 kB"

def test_promotion_after_rounding_binary():
    """Test promotion to next unit after rounding in binary mode."""
    # 1023.999... KiB rounds to 1024.0 KiB, must promote to 1.0 MiB
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"

def test_all_units_si():
    """Test all SI units: kB, MB, GB, TB, PB."""
    assert impl.format_bytes(1_000) == "1.0 kB"
    assert impl.format_bytes(1_000_000) == "1.0 MB"
    assert impl.format_bytes(1_000_000_000) == "1.0 GB"
    assert impl.format_bytes(1_000_000_000_000) == "1.0 TB"
    assert impl.format_bytes(1_000_000_000_000_000) == "1.0 PB"

def test_all_units_binary():
    """Test all binary units: KiB, MiB, GiB, TiB, PiB."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1_048_576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1_073_741_824, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1_099_511_627_776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1_125_899_906_842_624, binary=True) == "1.0 PiB"

def test_large_values_above_top_unit():
    """Test values that exceed the top unit (PB/PiB)."""
    # Grows inside PB, no capping
    assert impl.format_bytes(1_500_000_000_000_000_000) == "1500.0 PB"
    # 2**60 bytes in binary = 1024.0 PiB
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"

def test_negative_numbers_si():
    """Test negative numbers in SI mode."""
    assert impl.format_bytes(-999) == "-999 B"
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1_000_000) == "-1.0 MB"

def test_negative_numbers_binary():
    """Test negative numbers in binary mode."""
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"

def test_negative_with_promotion():
    """Negative values promote the same way as positive."""
    assert impl.format_bytes(-999_950) == "-1.0 MB"
    assert impl.format_bytes(-1_048_575, binary=True) == "-1.0 MiB"

def test_type_error_float():
    """TypeError for float input, even if whole-valued."""
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)
    with pytest.raises(TypeError):
        impl.format_bytes(1.5)

def test_type_error_string():
    """TypeError for string input."""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")

def test_type_error_none():
    """TypeError for None input."""
    with pytest.raises(TypeError):
        impl.format_bytes(None)

def test_type_error_bool():
    """TypeError for bool input (even though bool is subclass of int)."""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)

def test_spec_worked_examples():
    """Validate all worked examples from the ticket spec."""
    # SI examples
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1150) == "1.2 kB"
    assert impl.format_bytes(999_949) == "999.9 kB"
    assert impl.format_bytes(999_950) == "1.0 MB"
    assert impl.format_bytes(1_048_575) == "1.0 MB"
    
    # Binary examples
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"
    assert impl.format_bytes(999_949, binary=True) == "976.5 KiB"
    assert impl.format_bytes(999_950, binary=True) == "976.5 KiB"
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"
    
    # Negative examples
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"

def test_formatting_rules():
    """Test formatting rules: spacing, decimals, casing."""
    # B unit: no decimal point
    result_b = impl.format_bytes(500)
    assert result_b == "500 B"
    assert "." not in result_b
    
    # Non-B units: exactly one decimal place
    result_kb = impl.format_bytes(1500)
    assert result_kb == "1.5 kB"
    assert result_kb.count(".") == 1
    
    # Exactly one space between number and unit
    assert result_kb.count(" ") == 1
    assert "  " not in result_kb
    
    # SI: lowercase k, uppercase others
    assert "kB" in impl.format_bytes(1000)
    assert "MB" in impl.format_bytes(1_000_000)
    
    # Binary: uppercase K for kilo
    assert "KiB" in impl.format_bytes(1024, binary=True)
    assert "MiB" in impl.format_bytes(1_048_576, binary=True)
