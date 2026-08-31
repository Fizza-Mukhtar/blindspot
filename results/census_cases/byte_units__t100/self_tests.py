import pytest
import impl
from decimal import Decimal


def test_format_bytes_rejects_float():
    """format_bytes should reject float arguments."""
    with pytest.raises(TypeError):
        impl.format_bytes(1.0)
    with pytest.raises(TypeError):
        impl.format_bytes(1.5)


def test_format_bytes_rejects_str():
    """format_bytes should reject string arguments."""
    with pytest.raises(TypeError):
        impl.format_bytes("100")


def test_format_bytes_rejects_none():
    """format_bytes should reject None."""
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_format_bytes_rejects_decimal():
    """format_bytes should reject Decimal arguments."""
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal("100"))


def test_format_bytes_rejects_bool():
    """format_bytes should reject bool arguments, despite bool subclassing int."""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_format_bytes_zero():
    """Zero bytes should format to '0 B' in both modes."""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"


def test_format_bytes_negative():
    """Negative byte counts should prepend '-' to the formatted absolute value."""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-1000) == "-1.0 kB"
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"
    assert impl.format_bytes(-1500000000000000000) == "-1500.0 PB"


def test_format_bytes_byte_unit():
    """B unit values should display as plain integers without decimal point."""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_format_bytes_si_kilobyte():
    """Test SI kB prefix (1000 bytes threshold)."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1050) == "1.1 kB"
    assert impl.format_bytes(1150) == "1.2 kB"


def test_format_bytes_si_rounding_half_up():
    """Test half-up rounding behavior in SI mode."""
    # 1005 bytes = 1.005 kB, rounds to 1.0 kB (0.005 < 0.05)
    assert impl.format_bytes(1005) == "1.0 kB"
    # 1015 bytes = 1.015 kB, rounds to 1.0 kB (0.015 < 0.05)
    assert impl.format_bytes(1015) == "1.0 kB"
    # 999949 bytes = 999.949 kB, rounds to 999.9 kB
    assert impl.format_bytes(999949) == "999.9 kB"


def test_format_bytes_si_promotion():
    """Test that rounding can promote to the next unit in SI mode."""
    # 999950 bytes = 999.95 kB, rounds to 1000.0 kB, promotes to 1.0 MB
    assert impl.format_bytes(999950) == "1.0 MB"
    # 1 byte less should not promote
    assert impl.format_bytes(999949) == "999.9 kB"


def test_format_bytes_si_larger_units():
    """Test SI MB, GB, TB, PB units."""
    assert impl.format_bytes(1000000) == "1.0 MB"
    assert impl.format_bytes(1000000000) == "1.0 GB"
    assert impl.format_bytes(1000000000000) == "1.0 TB"
    assert impl.format_bytes(1000000000000000) == "1.0 PB"


def test_format_bytes_si_large_numbers():
    """Test very large numbers in SI mode (above PB)."""
    # 1500 PB
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"
    # Multiple PB
    assert impl.format_bytes(9999000000000000000) == "9999.0 PB"


def test_format_bytes_binary_kibibyte():
    """Test IEC KiB prefix (1024 bytes threshold)."""
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"


def test_format_bytes_binary_promotion():
    """Test that rounding can promote to the next unit in binary mode."""
    # 1048575 bytes = 1023.999... KiB, rounds to 1024.0 KiB, promotes to 1.0 MiB
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_format_bytes_binary_larger_units():
    """Test IEC MiB, GiB, TiB, PiB units."""
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"  # 2^20
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"  # 2^30
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"  # 2^40
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"  # 2^50


def test_format_bytes_binary_large_numbers():
    """Test very large numbers in binary mode (above PiB)."""
    # 2^60 = 1024 PiB
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"
    # 2^63 (still valid, stays in PiB range)
    result = impl.format_bytes(2**63, binary=True)
    assert result.endswith(" PiB")
    # Should have exactly 1 decimal place
    assert "." in result
    parts = result.split(" ")
    assert len(parts[0].split(".")[1]) == 1


def test_format_bytes_spacing_and_format():
    """Test that formatting has exactly one space and correct separators."""
    result = impl.format_bytes(1500)
    # Should be exactly "1.5 kB" with one space
    assert result == "1.5 kB"
    assert result.count(" ") == 1
    # Decimal separator is always dot
    assert "." in result
    # No thousands separators
    assert "," not in result
