import decimal

import pytest

import impl


def test_zero_bytes():
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"


@pytest.mark.parametrize("n,binary,expected", [
    (999, False, "999 B"),
    (999, True, "999 B"),
    (1, False, "1 B"),
    (1023, True, "1023 B"),
])
def test_plain_integer_below_first_unit(n, binary, expected):
    assert impl.format_bytes(n, binary=binary) == expected


def test_si_kilo_boundary():
    assert impl.format_bytes(1000) == "1.0 kB"
    # 1024 bytes in SI mode is still just over one kB, not a binary unit
    assert impl.format_bytes(1024) == "1.0 kB"


def test_binary_kilo_boundary():
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"


def test_round_half_up_si():
    # 1150 / 1000 = 1.15 -> rounds half up to 1.2, not banker's rounding to 1.1
    assert impl.format_bytes(1150) == "1.2 kB"


def test_round_half_up_binary():
    # 1150 / 1024 = 1.1230... -> rounds to 1.1
    assert impl.format_bytes(1150, binary=True) == "1.1 KiB"


def test_promotion_si_at_boundary():
    # 999_950 / 1000 = 999.95 -> rounds to 1000.0 kB which must promote to 1.0 MB
    assert impl.format_bytes(999_950) == "1.0 MB"
    assert impl.format_bytes(999_949) == "999.9 kB"


def test_no_promotion_one_byte_below_si():
    # explicitly confirm the boundary is exact: 999_949 does NOT promote
    result = impl.format_bytes(999_949)
    assert result == "999.9 kB"
    assert "1000.0" not in result


def test_promotion_binary_at_boundary():
    # 1_048_575 bytes = 1023.999... KiB -> rounds to 1024.0 KiB -> promote to 1.0 MiB
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"
    # same raw byte count in SI mode is below the MB threshold differently
    assert impl.format_bytes(1_048_575) == "1.0 MB"


def test_binary_unaffected_by_si_promotion_input():
    # 999_950 bytes does not reach the KiB/MiB boundary, so no promotion in binary mode
    assert impl.format_bytes(999_950, binary=True) == "976.5 KiB"


def test_negative_values():
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"
    assert impl.format_bytes(-999) == "-999 B"
    assert impl.format_bytes(-0) == "0 B"


def test_top_of_ladder_no_cap_si():
    assert impl.format_bytes(1_500_000_000_000_000_000) == "1500.0 PB"


def test_top_of_ladder_no_cap_binary():
    assert impl.format_bytes(2 ** 60, binary=True) == "1024.0 PiB"


def test_default_is_si():
    assert impl.format_bytes(1000) == impl.format_bytes(1000, binary=False)


@pytest.mark.parametrize("bad", [
    1000.0,
    3.14,
    "1000",
    None,
    decimal.Decimal(1000),
])
def test_type_error_for_non_int_types(bad):
    with pytest.raises(TypeError):
        impl.format_bytes(bad)


def test_type_error_for_bool():
    with pytest.raises(TypeError):
        impl.format_bytes(True)
    with pytest.raises(TypeError):
        impl.format_bytes(False)


def test_large_arbitrary_precision_int_does_not_raise():
    huge = 10 ** 30
    result = impl.format_bytes(huge)
    assert result.endswith(" PB")
    assert "," not in result


def test_formatting_has_single_space_and_no_thousands_separator():
    result = impl.format_bytes(999_950)
    assert result.count(" ") == 1
    assert "," not in result
    number_part = result.split(" ")[0]
    assert number_part == "1.0"
