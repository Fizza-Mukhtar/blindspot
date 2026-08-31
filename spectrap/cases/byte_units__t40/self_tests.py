import impl
import pytest
from decimal import Decimal


def test_zero():
    """Zero should format as '0 B'."""
    assert impl.format_bytes(0) == "0 B"


def test_single_byte():
    """Single byte should format as '1 B' in both SI and IEC."""
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(1, binary=True) == "1 B"


def test_bytes_without_promotion():
    """Multiple bytes below the first unit boundary."""
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_si_unit_sequence():
    """Test SI unit transitions: B, kB, MB, GB, TB, PB."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"
    assert impl.format_bytes(1000000) == "1.0 MB"
    assert impl.format_bytes(1000000000) == "1.0 GB"
    assert impl.format_bytes(1000000000000) == "1.0 TB"
    assert impl.format_bytes(1000000000000000) == "1.0 PB"


def test_iec_unit_sequence():
    """Test IEC unit transitions: B, KiB, MiB, GiB, TiB, PiB."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1536, binary=True) == "1.5 KiB"
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"


def test_si_iec_divergence_1024():
    """1024 bytes: 1.0 kB in SI, 1.0 KiB in IEC."""
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"


def test_si_iec_divergence_1000():
    """1000 bytes: 1.0 kB in SI, still 1000 B in IEC."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1000, binary=True) == "1000 B"


def test_rounding_half_up_si():
    """Rounding uses half-up, not half-to-even."""
    assert impl.format_bytes(1150) == "1.2 kB"  # 1.15 → 1.2
    assert impl.format_bytes(1050) == "1.1 kB"  # 1.05 → 1.1
    assert impl.format_bytes(1049) == "1.0 kB"  # 1.049 → 1.0


def test_rounding_triggers_promotion():
    """Rounding can carry a value onto the next unit boundary."""
    # 999.95 kB rounds to 1000.0 kB, which is 1.0 MB
    assert impl.format_bytes(999950) == "1.0 MB"
    # 999.949 kB rounds to 999.9 kB (stays in kB)
    assert impl.format_bytes(999949) == "999.9 kB"
    # Binary: 1048575 (2^20 - 1) rounds to 1.0 MiB
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_negative_numbers():
    """Negative values format as minus sign plus formatted magnitude."""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1000000) == "-1.0 MB"
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"


def test_very_large_numbers():
    """Numbers above the top unit keep growing the integer part."""
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_type_error_float():
    """Float values raise TypeError, including whole numbers like 1000.0."""
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)


def test_type_error_string():
    """String values raise TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")


def test_type_error_none():
    """None raises TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_type_error_decimal():
    """Decimal values raise TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal("1000"))


def test_type_error_bool():
    """Boolean values raise TypeError despite bool being a subtype of int."""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_formatting_details():
    """Verify format: exactly one decimal in non-byte units, integer in bytes, single space."""
    # Exactly one decimal place for non-byte units
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"
    # Integer (no decimal) for bytes only
    assert impl.format_bytes(500) == "500 B"
    # Single space between number and unit
    result = impl.format_bytes(1500)
    assert result.count(" ") == 1
    assert result == "1.5 kB"


def test_binary_parameter_defaults_to_si():
    """The binary parameter defaults to False, selecting SI prefixes."""
    assert impl.format_bytes(1024) == "1.0 kB"
    assert impl.format_bytes(1024, binary=False) == "1.0 kB"
