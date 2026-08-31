import pytest
import impl


class TestArgumentValidation:
    def test_header_not_string(self):
        with pytest.raises(ValueError):
            impl.resolve_range(123, 100)
        with pytest.raises(ValueError):
            impl.resolve_range(None, 100)

    def test_length_not_int(self):
        with pytest.raises(ValueError):
            impl.resolve_range("bytes=0-10", 100.5)
        with pytest.raises(ValueError):
            impl.resolve_range("bytes=0-10", "100")

    def test_length_negative(self):
        with pytest.raises(ValueError):
            impl.resolve_range("bytes=0-10", -1)


class TestEmptyRepresentation:
    def test_empty_representation_raises_regardless_of_header(self):
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=0-0", 0)
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("invalid", 0)
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("", 0)


class TestValidRangeFormats:
    def test_standard_range_formats(self):
        """Test first-last, first-, and -suffix formats"""
        assert impl.resolve_range("bytes=0-499", 1000) == [(0, 499)]
        assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]
        assert impl.resolve_range("bytes=-500", 1000) == [(500, 999)]

    def test_multiple_ranges(self):
        assert impl.resolve_range("bytes=0-99,200-299,500-599", 1000) == [(0, 99), (200, 299), (500, 599)]

    def test_leading_zeros(self):
        assert impl.resolve_range("bytes=007-009", 1000) == [(7, 9)]
        assert impl.resolve_range("bytes=00-0009", 1000) == [(0, 9)]

    def test_case_insensitive_unit(self):
        assert impl.resolve_range("bytes=0-0", 100) == [(0, 0)]
        assert impl.resolve_range("Bytes=0-0", 100) == [(0, 0)]
        assert impl.resolve_range("BYTES=0-0", 100) == [(0, 0)]


class TestClamping:
    def test_last_greater_than_length_clamped(self):
        assert impl.resolve_range("bytes=0-9999", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=500-9999", 1000) == [(500, 999)]
        assert impl.resolve_range("bytes=999-1000", 1000) == [(999, 999)]

    def test_suffix_at_or_beyond_length_returns_whole(self):
        assert impl.resolve_range("bytes=-5000", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=-1000", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=-1001", 1000) == [(0, 999)]


class TestUnsatisfiableRanges:
    def test_first_at_or_beyond_length_unsatisfiable(self):
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=5000-5100", 1000)
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=1000-1999", 1000)

    def test_minus_zero_unsatisfiable(self):
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=-0", 1000)

    def test_unsatisfiable_specs_dropped_satisfiable_kept(self):
        """Unsatisfiable specs removed, satisfiable ones preserved in order"""
        assert impl.resolve_range("bytes=100-199,5000-5100,0-0", 1000) == [(100, 199), (0, 0)]
        assert impl.resolve_range("bytes=100-199,5000-5100,6000-6100,0-0", 1000) == [(100, 199), (0, 0)]

    def test_all_ranges_unsatisfiable_raises(self):
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=5000-5100,6000-6100", 1000)
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=-0,-0", 1000)


class TestInvalidHeaders:
    def test_unrecognized_unit_serves_whole(self):
        assert impl.resolve_range("items=0-5", 1000) == [(0, 999)]
        assert impl.resolve_range("kilobytes=0-5", 1000) == [(0, 999)]

    def test_non_digits_serve_whole(self):
        assert impl.resolve_range("bytes=abc-def", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=+5-9", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=1.5-9", 1000) == [(0, 999)]

    def test_syntax_errors_serve_whole(self):
        assert impl.resolve_range("bytes0-1", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=-", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=0-1-2", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=0-1;q=1", 1000) == [(0, 999)]

    def test_space_inside_spec_invalid(self):
        """Spaces inside a spec are invalid"""
        assert impl.resolve_range("bytes=0 - 1", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=0- 1", 1000) == [(0, 999)]

    def test_tab_inside_spec_invalid(self):
        assert impl.resolve_range("bytes=0\t-1", 1000) == [(0, 999)]

    def test_last_less_than_first_invalid(self):
        assert impl.resolve_range("bytes=5-3", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=500-100", 1000) == [(0, 999)]

    def test_empty_or_only_empty_elements(self):
        assert impl.resolve_range("", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=,,,", 1000) == [(0, 999)]


class TestWhitespaceAndEmptyElements:
    def test_whitespace_around_header_allowed(self):
        assert impl.resolve_range("  bytes=0-0  ", 100) == [(0, 0)]
        assert impl.resolve_range("\tbytes=0-0\t", 100) == [(0, 0)]

    def test_whitespace_around_elements_allowed(self):
        assert impl.resolve_range("bytes= 0-0 ", 100) == [(0, 0)]
        assert impl.resolve_range("bytes= 0-99 , 200-299 ", 1000) == [(0, 99), (200, 299)]

    def test_empty_elements_skipped(self):
        """Empty elements between commas are silently skipped"""
        assert impl.resolve_range("bytes=0-0,,-1", 100) == [(0, 0), (99, 99)]
        assert impl.resolve_range("bytes=0-0,", 100) == [(0, 0)]
        assert impl.resolve_range("bytes=,0-0", 100) == [(0, 0)]
        assert impl.resolve_range("bytes=,,0-0,,", 100) == [(0, 0)]


class TestEdgeCases:
    def test_single_byte_edge_cases(self):
        assert impl.resolve_range("bytes=0-0", 1) == [(0, 0)]
        assert impl.resolve_range("bytes=0-", 1) == [(0, 0)]
        assert impl.resolve_range("bytes=-1", 1) == [(0, 0)]

    def test_boundary_conditions(self):
        assert impl.resolve_range("bytes=999-999", 1000) == [(999, 999)]
        assert impl.resolve_range("bytes=999-", 1000) == [(999, 999)]
        assert impl.resolve_range("bytes=-1", 1000) == [(999, 999)]

    def test_open_ended_range_boundary(self):
        assert impl.resolve_range("bytes=0-", 1000) == [(0, 999)]
        assert impl.resolve_range("bytes=500-", 1000) == [(500, 999)]
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=1000-", 1000)

    def test_order_preserved(self):
        """Ranges returned in order they appear"""
        assert impl.resolve_range("bytes=500-599,0-99,200-299", 1000) == [(500, 599), (0, 99), (200, 299)]
        result = impl.resolve_range("bytes=500-599,5000-5100,0-99,6000-6100,200-299", 1000)
        assert result == [(500, 599), (0, 99), (200, 299)]


class TestExceptionType:
    def test_unsatisfiable_range_is_exception_not_valueerror(self):
        assert issubclass(impl.UnsatisfiableRange, Exception)
        assert not issubclass(impl.UnsatisfiableRange, ValueError)
        with pytest.raises(impl.UnsatisfiableRange):
            impl.resolve_range("bytes=-0", 100)
