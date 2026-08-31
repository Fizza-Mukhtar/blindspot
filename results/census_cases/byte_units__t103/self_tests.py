import pytest
from decimal import Decimal
import impl


def test_zero():
    assert impl.format_bytes(0) == "0 B"


def test_single_byte():
    assert impl.format_bytes(1) == "1 B"


def test_bytes_before_unit_change():
    assert impl.format_bytes(999) == "999 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_si_units_1kb_to_1pb():
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1000000) == "1.0 MB"
    assert impl.format_bytes(1000000000) == "1.0 GB"
    assert impl.format_bytes(1000000000000) == "1.0 TB"
    assert impl.format_bytes(1000000000000000) == "1.0 PB"


def test_iec_units_1kib_to_1pib():
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"


def test_si_rounding_half_up():
    assert impl.format_bytes(1150) == "1.2 kB"
    assert impl.format_bytes(1050) == "1.1 kB"
    assert impl.format_bytes(1234) == "1.2 kB"
    assert impl.format_bytes(1245) == "1.2 kB"
    assert impl.format_bytes(1250) == "1.3 kB"


def test_si_rounding_promotes_to_mb():
    assert impl.format_bytes(999950) == "1.0 MB"


def test_iec_rounding_promotes_to_mib():
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


def test_si_large_beyond_pb():
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"
    assert impl.format_bytes(9999000000000000000) == "9999.0 PB"


def test_iec_large_beyond_pib():
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"
    assert impl.format_bytes(2**70, binary=True) == "1048576.0 PiB"


def test_negative_si():
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1000) == "-1.0 kB"


def test_negative_iec():
    assert impl.format_bytes(-2048, binary=True) == "-2.0 KiB"
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"


def test_type_error_float():
    with pytest.raises(TypeError):
        impl.format_bytes(1000.0)


def test_type_error_bool():
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_type_error_string():
    with pytest.raises(TypeError):
        impl.format_bytes("1000")


def test_type_error_none():
    with pytest.raises(TypeError):
        impl.format_bytes(None)


def test_type_error_decimal():
    with pytest.raises(TypeError):
        impl.format_bytes(Decimal("1000"))
