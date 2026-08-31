"""Regression test for: When a first-last spec's last-byte-pos is greater than or equal to length, clamp it to length - 1 instead of treating it as unsatisfiable.

Specification:
    clamped to `length - 1`

Found by Blindspot (OB-002, boundary probe).
"""

import impl


def test_range_clamping():
    result = impl.resolve_range('bytes=500-500', 1)
    assert result == [(0, 0)]
