import pytest
import impl


# ===== Type Validation =====

def test_type_error_bool():
    """format_bytes must reject bool values."""
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_type_error_float():
    """format_bytes must reject float, even whole-valued."""
    with pytest.raises(TypeError):
        impl.format_bytes(1.0)


def test_type_error_string_and_none():
    """format_bytes must reject string and None."""
    with pytest.raises(TypeError):
        impl.format_bytes("1000")
    with pytest.raises(TypeError):
        impl.format_bytes(None)


# ===== SI Prefix Tests (binary=False) =====

def test_si_zero_and_bytes():
    """Zero and small byte counts stay in B unit."""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(1) == "1 B"
    assert impl.format_bytes(999) == "999 B"


def test_si_kilobyte():
    """1000 bytes and up formats with one decimal in kB."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(1500) == "1.5 kB"


def test_si_megabyte_and_up():
    """Test MB and larger units."""
    assert impl.format_bytes(1000000) == "1.0 MB"
    assert impl.format_bytes(1000000000) == "1.0 GB"
    assert impl.format_bytes(1000000000000) == "1.0 TB"
    assert impl.format_bytes(1000000000000000) == "1.0 PB"


def test_si_above_peta():
    """Numbers above peta continue to grow in PB unit."""
    assert impl.format_bytes(1500000000000000000) == "1500.0 PB"


# ===== IEC Prefix Tests (binary=True) =====

def test_iec_zero_and_bytes():
    """Zero and small byte counts stay in B unit for IEC."""
    assert impl.format_bytes(0, binary=True) == "0 B"
    assert impl.format_bytes(1, binary=True) == "1 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_iec_kibibyte_and_up():
    """1024 bytes and up formats with one decimal in KiB."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1536, binary=True) == "1.5 KiB"
    assert impl.format_bytes(1048576, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1073741824, binary=True) == "1.0 GiB"


def test_iec_tebi_and_pebi():
    """Test TiB and PiB units."""
    assert impl.format_bytes(1099511627776, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1125899906842624, binary=True) == "1.0 PiB"


def test_iec_above_pebi():
    """Numbers above pebi continue to grow in PiB unit."""
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


# ===== Rounding Tests =====

def test_rounding_half_up():
    """Half-up rounding: 1050 → 1.1 kB, 1150 → 1.2 kB."""
    assert impl.format_bytes(1050) == "1.1 kB"
    assert impl.format_bytes(1150) == "1.2 kB"


def test_rounding_below_half():
    """Values below .5 round down: 999949 → 999.9 kB."""
    assert impl.format_bytes(999949) == "999.9 kB"


def test_rounding_with_promotion():
    """Rounding can promote to next unit (999950 → 1.0 MB)."""
    assert impl.format_bytes(999950) == "1.0 MB"
    assert impl.format_bytes(1048575, binary=True) == "1.0 MiB"


# ===== Negative Number Tests =====

def test_negative_format():
    """Negative numbers format as '-' followed by positive format."""
    assert impl.format_bytes(-1) == "-1 B"
    assert impl.format_bytes(-999) == "-999 B"
    assert impl.format_bytes(-1000) == "-1.0 kB"
    assert impl.format_bytes(-1500) == "-1.5 kB"


def test_negative_with_promotion():
    """Negative numbers also promote on rounding."""
    assert impl.format_bytes(-999950) == "-1.0 MB"
    assert impl.format_bytes(-1024, binary=True) == "-1.0 KiB"
