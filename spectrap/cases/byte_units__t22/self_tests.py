import pytest
import impl


def test_zero():
    """Zero is always '0 B'."""
    assert impl.format_bytes(0) == "0 B"


def test_single_byte():
    """Single byte is '1 B'."""
    assert impl.format_bytes(1) == "1 B"


def test_small_bytes_no_prefix():
    """Small values stay in B unit."""
    assert impl.format_bytes(500) == "500 B"


def test_si_kilo_boundary():
    """1000 bytes is exactly 1.0 kB in SI."""
    assert impl.format_bytes(1000) == "1.0 kB"


def test_si_mega():
    """1.5 MB in SI."""
    assert impl.format_bytes(1500000) == "1.5 MB"


def test_si_above_peta():
    """Values above PB continue growing without bound."""
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"


def test_binary_1000_bytes():
    """1000 bytes is still '1000 B' in binary (not '1.0 KiB')."""
    assert impl.format_bytes(1000, binary=True) == "1000 B"


def test_binary_kibibyte_boundary():
    """1024 bytes is exactly 1.0 KiB in binary."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"


def test_binary_above_pebibyte():
    """2^60 bytes is 1024.0 PiB (PiB is the top of the ladder)."""
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_rounding_half_up_1150():
    """1150 bytes = 1.15 kB, rounds half-up to 1.2 kB."""
    assert impl.format_bytes(1150) == "1.2 kB"


def test_rounding_half_up_1050():
    """1050 bytes = 1.05 kB, rounds half-up to 1.1 kB."""
    assert impl.format_bytes(1050) == "1.1 kB"


def test_rounding_promotes_to_next_unit_si():
    """999950 bytes = 999.95 kB, rounds to 1000.0 kB, promotes to 1.0 MB."""
    assert impl.format_bytes(999950) == "1.0 MB"


def test_rounding_no_promotion_si():
    """999949 bytes = 999.949 kB, rounds to 999.9 kB without promotion."""
    assert impl.format_bytes(999949) == "999.9 kB"


def test_rounding_promotes_to_next_unit_binary():
    """1048575 bytes = 1023.999... KiB, rounds to 1024.0 KiB, promotes to 1.0 MiB."""
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_negative_value():
    """Negative values prepend '-' to the formatted magnitude."""
    assert impl.format_bytes(-1500) == "-1.5 kB"


def test_type_error_float():
    """Float raises TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)


def test_type_error_bool():
    """bool raises TypeError (even though bool is a subclass of int)."""
    with pytest.raises(TypeError):
        impl.format_bytes(True)


def test_type_error_string():
    """String raises TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")


def test_type_error_none():
    """None raises TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_type_error_decimal():
    """Decimal raises TypeError."""
    from decimal import Decimal
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal('1000'))
