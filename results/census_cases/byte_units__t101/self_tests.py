import pytest
import impl
from decimal import Decimal


def test_zero():
    """Zero bytes should return '0 B'."""
    assert impl.format_bytes(0) == "0 B"


def test_bytes_unchanged():
    """Small values should remain in bytes unit."""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_si_kilobyte():
    """Test SI kilobyte formatting."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"


def test_si_megabyte():
    """Test SI megabyte formatting."""
    assert impl.format_bytes(1000000) == "1.0 MB"


def test_si_gigabyte():
    """Test SI gigabyte formatting."""
    assert impl.format_bytes(1000000000) == "1.0 GB"


def test_si_terabyte():
    """Test SI terabyte formatting."""
    assert impl.format_bytes(1000000000000) == "1.0 TB"


def test_si_petabyte():
    """Test SI petabyte formatting (top of ladder)."""
    assert impl.format_bytes(1000000000000000) == "1.0 PB"
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"


def test_iec_kibibyte():
    """Test IEC kibibyte formatting."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1536, binary=True) == "1.5 KiB"


def test_iec_mebibyte():
    """Test IEC mebibyte formatting."""
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"


def test_iec_gibibyte():
    """Test IEC gibibyte formatting."""
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"


def test_iec_tebibyte():
    """Test IEC tebibyte formatting."""
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"


def test_iec_pebibyte():
    """Test IEC pebibyte formatting (top of ladder)."""
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_rounding_half_up():
    """Test half-up rounding at various thresholds."""
    # 1050 / 1000 = 1.05 -> rounds to 1.1
    assert impl.format_bytes(1050) == "1.1 kB"
    # 1150 / 1000 = 1.15 -> rounds to 1.2
    assert impl.format_bytes(1150) == "1.2 kB"
    # 1950 / 1000 = 1.95 -> rounds to 2.0
    assert impl.format_bytes(1950) == "2.0 kB"


def test_promotion_si():
    """Test rounding-induced promotion to next unit (SI)."""
    # 999950 / 1000 = 999.95 -> rounds to 1000.0 -> promotes to 1.0 MB
    assert impl.format_bytes(999950) == "1.0 MB"


def test_promotion_iec():
    """Test rounding-induced promotion to next unit (IEC)."""
    # 1048575 / 1024 = 1023.999... -> rounds to 1024.0 -> promotes to 1.0 MiB
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_no_promotion_boundary():
    """Test that values just below rounding threshold don't promote."""
    # 999949 / 1000 = 999.949 -> rounds to 999.9 (no promotion)
    assert impl.format_bytes(999949) == "999.9 kB"


def test_negative_numbers():
    """Test negative byte counts."""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-1000) == "-1.0 kB"
    assert impl.format_bytes(-999950) == "-1.0 MB"


def test_type_errors():
    """Test that invalid types raise TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)
    with pytest.raises(TypeError):
        impl.format_bytes("1000")
    with pytest.raises(TypeError):
        impl.format_bytes(None)
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal("1000"))
