import pytest
import impl


class TestApplyDiscounts:
    """Comprehensive test suite for apply_discounts function."""

    # Core functionality tests
    def test_empty_discounts(self):
        """Empty discounts list returns normalized subtotal."""
        assert impl.apply_discounts("100.00", []) == "100.00"

    def test_single_percentage_discount(self):
        """Apply single percentage discount."""
        assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "20"}]) == "80.00"

    def test_single_amount_discount(self):
        """Apply single amount discount."""
        assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "5.00"}]) == "95.00"

    def test_multiple_discounts_compound(self):
        """Multiple discounts compound: 20% then 5.00 then 10% gives 67.50."""
        discounts = [
            {"kind": "percent", "value": "20"},
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "10"}
        ]
        # 100 → 80 → 75 → 67.50
        assert impl.apply_discounts("100.00", discounts) == "67.50"

    def test_multiple_discounts_different_order(self):
        """Discounts applied in order given: 5.00 then 20% then 10% gives 68.40."""
        discounts = [
            {"kind": "amount", "value": "5.00"},
            {"kind": "percent", "value": "20"},
            {"kind": "percent", "value": "10"}
        ]
        # 100 → 95 → 76 → 68.40
        assert impl.apply_discounts("100.00", discounts) == "68.40"

    def test_fractional_percentage(self):
        """Fractional percentage discount (12.5%)."""
        assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "12.5"}]) == "87.50"

    def test_zero_subtotal_with_discounts(self):
        """Zero subtotal with discounts remains zero."""
        assert impl.apply_discounts("0.00", [{"kind": "percent", "value": "50"}]) == "0.00"

    def test_amount_discount_exceeds_total(self):
        """Amount discount larger than total clamps to 0.00."""
        assert impl.apply_discounts("50.00", [{"kind": "amount", "value": "100.00"}]) == "0.00"

    # Edge cases
    def test_100_percent_discount(self):
        """100% discount is allowed and brings total to 0.00."""
        assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "100"}]) == "0.00"

    def test_negative_zero_subtotal(self):
        """Negative zero (-0.00) is treated as zero."""
        assert impl.apply_discounts("-0.00", []) == "0.00"

    def test_subtotal_normalization(self):
        """Subtotal is normalized to exactly 2 decimal places."""
        assert impl.apply_discounts("100.1", []) == "100.10"
        assert impl.apply_discounts("100.12345", []) == "100.12"

    def test_zero_value_discounts(self):
        """Zero value discounts do not change total."""
        assert impl.apply_discounts("100.00", [{"kind": "percent", "value": "0"}]) == "100.00"
        assert impl.apply_discounts("100.00", [{"kind": "amount", "value": "0.00"}]) == "100.00"

    def test_discounts_after_total_reaches_zero(self):
        """Discounts after total reaches zero still operate on 0.00."""
        discounts = [
            {"kind": "amount", "value": "100.00"},
            {"kind": "percent", "value": "50"}
        ]
        assert impl.apply_discounts("50.00", discounts) == "0.00"

    # Error validation: subtotal
    def test_error_subtotal_not_string(self):
        """Error when subtotal is not a string."""
        with pytest.raises(ValueError, match="subtotal is not a str"):
            impl.apply_discounts(100.00, [])

    def test_error_subtotal_malformed(self):
        """Error when subtotal is malformed (violates grammar)."""
        with pytest.raises(ValueError, match="subtotal is malformed"):
            impl.apply_discounts("", [])
        with pytest.raises(ValueError, match="subtotal is malformed"):
            impl.apply_discounts("+100.00", [])
        with pytest.raises(ValueError, match="subtotal is malformed"):
            impl.apply_discounts(" 100.00", [])
        with pytest.raises(ValueError, match="subtotal is malformed"):
            impl.apply_discounts("5.", [])

    def test_error_subtotal_negative(self):
        """Error when subtotal is negative (but -0.00 is allowed)."""
        with pytest.raises(ValueError, match="subtotal is negative"):
            impl.apply_discounts("-100.00", [])

    # Error validation: discount structure
    def test_error_discount_not_mapping(self):
        """Error when discount is not a mapping."""
        with pytest.raises(ValueError, match="discount is not a mapping"):
            impl.apply_discounts("100.00", ["not a dict"])

    def test_error_discount_missing_keys(self):
        """Error when discount missing 'kind' or 'value'."""
        with pytest.raises(ValueError, match="discount is missing 'kind'"):
            impl.apply_discounts("100.00", [{"value": "50"}])
        with pytest.raises(ValueError, match="discount is missing 'value'"):
            impl.apply_discounts("100.00", [{"kind": "percent"}])

    # Error validation: discount kind and value
    def test_error_discount_kind_invalid(self):
        """Error when kind is not exactly 'percent' or 'amount'."""
        with pytest.raises(ValueError, match="kind is not 'percent' or 'amount'"):
            impl.apply_discounts("100.00", [{"kind": "Percent", "value": "50"}])

    def test_error_discount_value_invalid(self):
        """Error when value is not a string or is malformed."""
        with pytest.raises(ValueError, match="value is not a str"):
            impl.apply_discounts("100.00", [{"kind": "percent", "value": 50}])
        with pytest.raises(ValueError, match="value is malformed"):
            impl.apply_discounts("100.00", [{"kind": "percent", "value": ""}])
        with pytest.raises(ValueError, match="value is malformed"):
            impl.apply_discounts("100.00", [{"kind": "amount", "value": ".5"}])

    def test_error_discount_negative_value(self):
        """Error when discount value is negative (caught as malformed)."""
        with pytest.raises(ValueError, match="value is malformed"):
            impl.apply_discounts("100.00", [{"kind": "percent", "value": "-20"}])
        with pytest.raises(ValueError, match="value is malformed"):
            impl.apply_discounts("100.00", [{"kind": "amount", "value": "-5.00"}])

    def test_error_percent_exceeds_100(self):
        """Error when percent value is greater than 100."""
        with pytest.raises(ValueError, match="percent value is greater than 100"):
            impl.apply_discounts("100.00", [{"kind": "percent", "value": "101"}])

    def test_does_not_mutate_inputs(self):
        """Function does not mutate discounts list or inner dicts."""
        discounts = [{"kind": "percent", "value": "50"}]
        original = [{"kind": "percent", "value": "50"}]
        impl.apply_discounts("100.00", discounts)
        assert discounts == original
