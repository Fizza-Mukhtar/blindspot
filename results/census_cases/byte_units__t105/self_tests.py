import impl
import pytest
from decimal import Decimal


def test_zero():
    """Test zero returns '0 B'"""
    assert impl.format_bytes(0) == "0 B"


def test_bytes_si():
    """Test small byte values in SI"""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(500) == "500 B"
    assert impl.format_bytes(999) == "999 B"


def test_bytes_binary():
    """Test small byte values in binary"""
    assert impl.format_bytes(1, binary=True) == "1 B"
    assert impl.format_bytes(512, binary=True) == "512 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_kb_si():
    """Test kilobyte values in SI"""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"


def test_kib():
    """Test kibibyte values in binary"""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1536, binary=True) == "1.5 KiB"


def test_rounding_si():
    """Test rounding in SI (1049->1.0 kB, 1050->1.1 kB)"""
    assert impl.format_bytes(1049) == "1.0 kB"
    assert impl.format_bytes(1050) == "1.1 kB"


def test_rounding_carry_si():
    """Test that 999950 bytes rounds up to 1.0 MB in SI"""
    assert impl.format_bytes(999950) == "1.0 MB"


def test_rounding_carry_binary():
    """Test that 1048575 bytes rounds up to 1.0 MiB in binary"""
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_large_units_si():
    """Test MB, GB, TB, PB in SI"""
    assert impl.format_bytes(1000000) == "1.0 MB"
    assert impl.format_bytes(1000000000) == "1.0 GB"
    assert impl.format_bytes(1000000000000) == "1.0 TB"
    assert impl.format_bytes(1000000000000000) == "1.0 PB"


def test_large_units_binary():
    """Test MiB, GiB, TiB, PiB in binary"""
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"


def test_above_max_si():
    """Test values above PB in SI"""
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"


def test_above_max_binary():
    """Test values above PiB in binary"""
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_negative_si():
    """Test negative values in SI"""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-1000) == "-1.0 kB"
    assert impl.format_bytes(-999950) == "-1.0 MB"


def test_negative_binary():
    """Test negative values in binary"""
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"
    assert impl.format_bytes(-1048575, binary=True) == "-1.0 MiB"


def test_type_error_bool():
    """Test that bool raises TypeError"""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_type_error_float():
    """Test that float raises TypeError"""
    with pytest.raises(TypeError):
        impl.format_bytes(1.0)
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)


def test_type_error_string():
    """Test that string raises TypeError"""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")


def test_type_error_none():
    """Test that None raises TypeError"""
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_type_error_decimal():
    """Test that Decimal raises TypeError"""
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal('1000'))


def test_no_decimal_for_bytes():
    """Test that B unit never has decimal point"""
    assert "." not in impl.format_bytes(1)
    assert "." not in impl.format_bytes(999)
