import pytest
import impl


def test_format_bytes_zero():
    """Test zero bytes"""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"


def test_format_bytes_below_thousand_si():
    """Test SI mode with bytes below 1000"""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"


def test_format_bytes_kilobytes_si():
    """Test SI kilobyte formatting"""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1150) == "1.2 kB"


def test_format_bytes_kilobytes_no_promotion_si():
    """Test SI kilobytes without promotion"""
    assert impl.format_bytes(999_949) == "999.9 kB"


def test_format_bytes_promotion_si():
    """Test SI promotion after rounding"""
    assert impl.format_bytes(999_950) == "1.0 MB"


def test_format_bytes_larger_units_si():
    """Test SI megabytes, gigabytes, terabytes, petabytes"""
    assert impl.format_bytes(1_000_000) == "1.0 MB"
    assert impl.format_bytes(1_048_575) == "1.0 MB"
    assert impl.format_bytes(1_000_000_000) == "1.0 GB"
    assert impl.format_bytes(1_000_000_000_000) == "1.0 TB"
    assert impl.format_bytes(1_000_000_000_000_000) == "1.0 PB"


def test_format_bytes_negative_si():
    """Test negative numbers in SI mode"""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-999_950) == "-1.0 MB"
    assert impl.format_bytes(-1_000_000_000) == "-1.0 GB"


def test_format_bytes_below_1024_binary():
    """Test binary mode with bytes below 1024"""
    assert impl.format_bytes(1, binary=True) == "1 B"
    assert impl.format_bytes(999, binary=True) == "999 B"
    assert impl.format_bytes(1000, binary=True) == "1000 B"


def test_format_bytes_kibibytes_binary():
    """Test binary kibibyte formatting"""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"
    assert impl.format_bytes(999_949, binary=True) == "976.5 KiB"
    assert impl.format_bytes(999_950, binary=True) == "976.5 KiB"


def test_format_bytes_mebibytes_promotion_binary():
    """Test binary promotion to mebibytes"""
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1024**2, binary=True) == "1.0 MiB"


def test_format_bytes_larger_units_binary():
    """Test binary gibibytes, tebibytes, pebibytes"""
    assert impl.format_bytes(1024**3, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1024**4, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1024**5, binary=True) == "1.0 PiB"


def test_format_bytes_negative_binary():
    """Test negative numbers in binary mode"""
    assert impl.format_bytes(-1, binary=True) == "-1 B"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"
    assert impl.format_bytes(-1_048_575, binary=True) == "-1.0 MiB"
    assert impl.format_bytes(-1024**3, binary=True) == "-1.0 GiB"


def test_format_bytes_large_values():
    """Test large values at top of ladders"""
    assert impl.format_bytes(1_500_000_000_000_000_000) == "1500.0 PB"
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_format_bytes_type_error_float():
    """Test TypeError for float input"""
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)


def test_format_bytes_type_error_string():
    """Test TypeError for string input"""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")


def test_format_bytes_type_error_none():
    """Test TypeError for None input"""
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_format_bytes_type_error_decimal():
    """Test TypeError for Decimal input"""
    from decimal import Decimal
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal("1000"))


def test_format_bytes_type_error_bool():
    """Test TypeError for bool input"""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    
    with pytest.raises(TypeError):
        impl.format_bytes(False)
