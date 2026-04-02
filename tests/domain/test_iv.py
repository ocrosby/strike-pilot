"""Unit tests for IV rank and percentile computations."""

from __future__ import annotations

import pytest

from strike_pilot.domain.iv import compute_iv_percentile, compute_iv_rank


class TestComputeIvRank:
    def test_midpoint(self) -> None:
        assert compute_iv_rank(current_iv=20.0, low_iv=10.0, high_iv=30.0) == pytest.approx(0.5)

    def test_at_low(self) -> None:
        assert compute_iv_rank(current_iv=10.0, low_iv=10.0, high_iv=30.0) == pytest.approx(0.0)

    def test_at_high(self) -> None:
        assert compute_iv_rank(current_iv=30.0, low_iv=10.0, high_iv=30.0) == pytest.approx(1.0)

    def test_above_high_clamped(self) -> None:
        assert compute_iv_rank(current_iv=40.0, low_iv=10.0, high_iv=30.0) == pytest.approx(1.0)

    def test_below_low_clamped(self) -> None:
        assert compute_iv_rank(current_iv=5.0, low_iv=10.0, high_iv=30.0) == pytest.approx(0.0)

    def test_equal_low_and_high_returns_zero(self) -> None:
        assert compute_iv_rank(current_iv=15.0, low_iv=15.0, high_iv=15.0) == 0.0

    def test_high_below_low_returns_zero(self) -> None:
        assert compute_iv_rank(current_iv=15.0, low_iv=20.0, high_iv=10.0) == 0.0


class TestComputeIvPercentile:
    def test_all_below(self) -> None:
        assert compute_iv_percentile(30.0, [10.0, 15.0, 20.0]) == pytest.approx(1.0)

    def test_none_below(self) -> None:
        assert compute_iv_percentile(5.0, [10.0, 15.0, 20.0]) == pytest.approx(0.0)

    def test_half_below(self) -> None:
        assert compute_iv_percentile(15.0, [10.0, 15.0, 20.0, 25.0]) == pytest.approx(0.25)

    def test_empty_history(self) -> None:
        assert compute_iv_percentile(15.0, []) == 0.0

    def test_single_value_below(self) -> None:
        assert compute_iv_percentile(20.0, [10.0]) == pytest.approx(1.0)

    def test_single_value_equal(self) -> None:
        assert compute_iv_percentile(10.0, [10.0]) == pytest.approx(0.0)
