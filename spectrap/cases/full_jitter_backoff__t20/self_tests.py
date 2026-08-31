import impl
import pytest
import math


class TestScheduleNormalPath:
    def test_basic_schedule(self):
        """Test basic schedule computation with exponential growth"""
        result = impl.schedule(3, 1.0, 10.0, lambda u: u)
        assert len(result) == 3
        assert result == [1.0, 2.0, 4.0]
    
    def test_ticket_example(self):
        """Test the exact example from the ticket"""
        result = impl.schedule(6, 0.2, 5.0, lambda u: u / 2)
        expected = [0.1, 0.2, 0.4, 0.8, 1.6, 2.5]
        assert len(result) == 6
        for r, e in zip(result, expected):
            assert abs(r - e) < 1e-10
    
    def test_empty_schedule(self):
        """Test that attempts=0 returns empty list"""
        result = impl.schedule(0, 1.0, 10.0, lambda u: u)
        assert result == []
    
    def test_single_attempt(self):
        """Test with exactly one attempt"""
        result = impl.schedule(1, 1.0, 10.0, lambda u: u)
        assert len(result) == 1
        assert result[0] == 1.0
    
    def test_cap_equals_base(self):
        """Test when cap equals base produces flat jittered delays"""
        result = impl.schedule(5, 2.0, 2.0, lambda u: u)
        assert all(r == 2.0 for r in result)
        assert len(result) == 5
    
    def test_rand_called_with_correct_ceilings(self):
        """Verify rand receives correct ceiling values in order"""
        ceilings_received = []
        def capturing_rand(u):
            ceilings_received.append(u)
            return 0.0
        
        impl.schedule(4, 1.0, 16.0, capturing_rand)
        assert ceilings_received == [1.0, 2.0, 4.0, 8.0]
    
    def test_rand_result_passed_through(self):
        """Verify rand results are used as-is without modification"""
        test_values = [0.5, 1.5, 2.5, 3.5]
        value_iter = iter(test_values)
        result = impl.schedule(4, 1.0, 10.0, lambda u: next(value_iter))
        assert result == test_values
    
    def test_large_attempts_no_overflow(self):
        """Test that 2000 attempts completes without overflow"""
        result = impl.schedule(2000, 1.0, 30.0, lambda u: 0.0)
        assert len(result) == 2000
        assert all(r == 0.0 for r in result)
    
    def test_cap_clamps_exponential_growth(self):
        """Test ceiling stops growing once cap is reached"""
        ceilings = []
        def capture_rand(u):
            ceilings.append(u)
            return 0.0
        
        impl.schedule(10, 1.0, 8.0, capture_rand)
        # Ceilings should be: 1, 2, 4, 8, then 8 for all remaining
        assert ceilings == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 8.0]


class TestScheduleValidationErrors:
    def test_negative_attempts(self):
        """Test that negative attempts raises ValueError"""
        with pytest.raises(ValueError, match="attempts"):
            impl.schedule(-1, 1.0, 10.0, lambda u: u)
    
    def test_base_zero(self):
        """Test that base=0 raises ValueError"""
        with pytest.raises(ValueError, match="base"):
            impl.schedule(1, 0.0, 10.0, lambda u: u)
    
    def test_base_negative(self):
        """Test that negative base raises ValueError"""
        with pytest.raises(ValueError, match="base"):
            impl.schedule(1, -0.5, 10.0, lambda u: u)
    
    def test_base_infinity(self):
        """Test that infinite base raises ValueError"""
        with pytest.raises(ValueError, match="base"):
            impl.schedule(1, float('inf'), 10.0, lambda u: u)
    
    def test_base_nan(self):
        """Test that NaN base raises ValueError"""
        with pytest.raises(ValueError, match="base"):
            impl.schedule(1, float('nan'), 10.0, lambda u: u)
    
    def test_cap_zero(self):
        """Test that cap=0 raises ValueError"""
        with pytest.raises(ValueError, match="cap"):
            impl.schedule(1, 1.0, 0.0, lambda u: u)
    
    def test_cap_negative(self):
        """Test that negative cap raises ValueError"""
        with pytest.raises(ValueError, match="cap"):
            impl.schedule(1, 1.0, -0.5, lambda u: u)
    
    def test_cap_infinity(self):
        """Test that infinite cap raises ValueError"""
        with pytest.raises(ValueError, match="cap"):
            impl.schedule(1, 1.0, float('inf'), lambda u: u)
    
    def test_cap_nan(self):
        """Test that NaN cap raises ValueError"""
        with pytest.raises(ValueError, match="cap"):
            impl.schedule(1, 1.0, float('nan'), lambda u: u)
    
    def test_validation_order_attempts_before_base(self):
        """Test that attempts is validated before base"""
        with pytest.raises(ValueError, match="attempts"):
            impl.schedule(-1, 0.0, 10.0, lambda u: u)
    
    def test_validation_order_base_before_cap(self):
        """Test that base is validated before cap"""
        with pytest.raises(ValueError, match="base"):
            impl.schedule(1, 0.0, 0.0, lambda u: u)
