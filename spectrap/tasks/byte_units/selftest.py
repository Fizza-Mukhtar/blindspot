"""Authoritative examples for PLAT-2291.

Every assertion here traces to a named clause of one of the cited standards or
to an explicit sentence of SPEC.md, never to whatever the reference
implementation happens to do.  ``make verify-corpus`` runs this against
``reference.py`` in CI, which is what lets the README claim that ground-truth
labels are verified by construction rather than by inspection.

Sources:
  * SI decimal prefixes (BIPM): https://www.bipm.org/en/measurement-units/si-prefixes
  * IEC 80000-13 binary prefixes: https://www.iec.ch/prefixes-binary-multiples
"""

import pytest

import impl


def test_zero_is_plain_bytes_with_no_decimal_point():
    """SPEC "How the number is rendered": `n = 0` produces `0 B`."""
    assert impl.format_bytes(0) == "0 B"
    assert impl.format_bytes(0, binary=True) == "0 B"


def test_si_below_the_divisor_stays_in_bytes():
    """SPEC: below the divisor, print the magnitude as a plain integer."""
    assert impl.format_bytes(999) == "999 B"


def test_si_kilo_symbol_is_lowercase_k():
    """BIPM SI prefixes: the symbol for kilo (10^3) is a lowercase `k`."""
    assert impl.format_bytes(1000) == "1.0 kB"


def test_si_divisor_is_1000_so_1024_is_not_a_unit_boundary():
    """SPEC "The two unit ladders": in SI the divisor is 1000, and 1024/1000
    rounds to 1.0, so 1024 bytes is still 1.0 kB -- not 1.0 KB and not 1 kB."""
    assert impl.format_bytes(1024) == "1.0 kB"


def test_iec_divisor_is_1024_so_1000_is_still_plain_bytes():
    """IEC 80000-13: 1 KiB = 2^10 = 1024 B, therefore 1000 B is below the
    first prefix step and prints with no decimal point."""
    assert impl.format_bytes(1000, binary=True) == "1000 B"
    assert impl.format_bytes(1023, binary=True) == "1023 B"


def test_iec_kibi_symbol_is_uppercase_ki():
    """IEC 80000-13: the symbol for kibi is `Ki`, capitalised."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"


def test_default_mode_is_si():
    """SPEC "What to build": `binary` defaults to False, i.e. SI."""
    assert impl.format_bytes(1024) == impl.format_bytes(1024, binary=False) == "1.0 kB"


def test_every_unit_above_bytes_shows_exactly_one_decimal_digit():
    """SPEC: for every unit above `B`, exactly one digit after the point."""
    assert impl.format_bytes(2000) == "2.0 kB"
    assert impl.format_bytes(2 * 1024, binary=True) == "2.0 KiB"


def test_si_unit_ladder():
    """BIPM: k/M/G/T/P are 10^3, 10^6, 10^9, 10^12, 10^15."""
    assert impl.format_bytes(1000) == "1.0 kB"
    assert impl.format_bytes(10**6) == "1.0 MB"
    assert impl.format_bytes(10**9) == "1.0 GB"
    assert impl.format_bytes(10**12) == "1.0 TB"
    assert impl.format_bytes(10**15) == "1.0 PB"


def test_iec_unit_ladder():
    """IEC 80000-13: Ki/Mi/Gi/Ti/Pi are 2^10, 2^20, 2^30, 2^40, 2^50."""
    assert impl.format_bytes(1024, binary=True) == "1.0 KiB"
    assert impl.format_bytes(1024**2, binary=True) == "1.0 MiB"
    assert impl.format_bytes(1024**3, binary=True) == "1.0 GiB"
    assert impl.format_bytes(1024**4, binary=True) == "1.0 TiB"
    assert impl.format_bytes(1024**5, binary=True) == "1.0 PiB"


def test_rounding_is_half_up_on_the_displayed_decimal():
    """SPEC "How the number is rendered": a displayed value of exactly x.x5
    rounds away from zero, so 1150 bytes is 1.2 kB (Python's `round` and IEEE
    double arithmetic both give 1.1 here)."""
    assert impl.format_bytes(1150) == "1.2 kB"
    assert impl.format_bytes(1050) == "1.1 kB"
    assert impl.format_bytes(1250) == "1.3 kB"


def test_si_promotion_when_rounding_reaches_the_next_boundary():
    """SPEC "Promotion after rounding": 999_950 B is 999.95 kB, which rounds
    half up to 1000.0 kB, and 1000.0 kB must be printed as 1.0 MB."""
    assert impl.format_bytes(999_950) == "1.0 MB"


def test_no_promotion_one_byte_below_the_rounding_edge():
    """SPEC "Promotion after rounding": one byte less does not promote."""
    assert impl.format_bytes(999_949) == "999.9 kB"


def test_iec_promotion_when_rounding_reaches_the_next_boundary():
    """SPEC "Promotion after rounding": 1_048_575 B is 1023.999... KiB, which
    rounds to 1024.0 KiB and must therefore be printed as 1.0 MiB."""
    assert impl.format_bytes(1_048_575, binary=True) == "1.0 MiB"


def test_negative_values_keep_the_sign_and_format_the_magnitude():
    """SPEC "How the number is rendered": a leading `-` followed by exactly
    what abs(n) would produce on its own."""
    assert impl.format_bytes(-1500) == "-1.5 kB"
    assert impl.format_bytes(-999) == "-999 B"
    assert impl.format_bytes(-1500, binary=True) == "-1.5 KiB"
    assert impl.format_bytes(-999_950) == "-1.0 MB"


def test_values_above_the_top_unit_stay_in_that_unit():
    """SPEC "Above the top of the ladder": PB/PiB are the largest units and
    the integer part is not capped."""
    assert impl.format_bytes(1_500_000_000_000_000_000) == "1500.0 PB"
    assert impl.format_bytes(2**60, binary=True) == "1024.0 PiB"


def test_single_space_between_number_and_unit():
    """SPEC: exactly one space between the number and the unit symbol, and no
    other whitespace, with `.` as the decimal separator."""
    for out in (
        impl.format_bytes(0),
        impl.format_bytes(999),
        impl.format_bytes(999_950),
        impl.format_bytes(-1024, binary=True),
    ):
        assert out.count(" ") == 1
        assert out == out.strip()
        assert "," not in out


@pytest.mark.parametrize("bad", [1000.0, 0.0, 1.5, "1000", None, (1,), 1000j])
def test_non_integer_input_raises_type_error(bad):
    """SPEC "Errors": anything that is not an `int` raises TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(bad)


@pytest.mark.parametrize("bad", [True, False])
def test_bool_is_rejected_even_though_it_subclasses_int(bad):
    """SPEC "Errors": `True` is not a byte count; format_bytes(True) must
    raise TypeError."""
    with pytest.raises(TypeError):
        impl.format_bytes(bad)
