"""Unit tests for expiry date resolution."""

from __future__ import annotations

from datetime import UTC, datetime

from strike_pilot.domain.expiry import (
    monthly_expiry,
    resolve_expiry,
    weekly_expiry,
    zero_dte_expiry,
)
from strike_pilot.domain.models import ExpiryCategory


class TestZeroDteExpiry:
    def test_returns_today(self) -> None:
        ref = datetime(2024, 3, 13, 10, 0, tzinfo=UTC)  # Wednesday
        assert zero_dte_expiry(ref) == "2024-03-13"

    def test_works_on_weekend(self) -> None:
        ref = datetime(2024, 3, 16, 10, 0, tzinfo=UTC)  # Saturday
        assert zero_dte_expiry(ref) == "2024-03-16"


class TestWeeklyExpiry:
    def test_monday_returns_friday(self) -> None:
        ref = datetime(2024, 3, 11, 10, 0, tzinfo=UTC)  # Monday
        assert weekly_expiry(ref) == "2024-03-15"

    def test_wednesday_returns_friday(self) -> None:
        ref = datetime(2024, 3, 13, 10, 0, tzinfo=UTC)  # Wednesday
        assert weekly_expiry(ref) == "2024-03-15"

    def test_friday_returns_same_day(self) -> None:
        ref = datetime(2024, 3, 15, 10, 0, tzinfo=UTC)  # Friday
        assert weekly_expiry(ref) == "2024-03-15"

    def test_saturday_returns_next_friday(self) -> None:
        ref = datetime(2024, 3, 16, 10, 0, tzinfo=UTC)  # Saturday
        assert weekly_expiry(ref) == "2024-03-22"

    def test_sunday_returns_next_friday(self) -> None:
        ref = datetime(2024, 3, 17, 10, 0, tzinfo=UTC)  # Sunday
        assert weekly_expiry(ref) == "2024-03-22"


class TestMonthlyExpiry:
    def test_before_third_friday(self) -> None:
        ref = datetime(2024, 3, 1, 10, 0, tzinfo=UTC)
        # Third Friday of March 2024 = March 15
        assert monthly_expiry(ref) == "2024-03-15"

    def test_on_third_friday(self) -> None:
        ref = datetime(2024, 3, 15, 10, 0, tzinfo=UTC)
        assert monthly_expiry(ref) == "2024-03-15"

    def test_after_third_friday_rolls_to_next_month(self) -> None:
        ref = datetime(2024, 3, 16, 10, 0, tzinfo=UTC)
        # Third Friday of April 2024 = April 19
        assert monthly_expiry(ref) == "2024-04-19"

    def test_december_rolls_to_january(self) -> None:
        ref = datetime(2024, 12, 25, 10, 0, tzinfo=UTC)
        # Third Friday of January 2025 = January 17
        assert monthly_expiry(ref) == "2025-01-17"

    def test_third_friday_of_january_2025(self) -> None:
        ref = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)
        assert monthly_expiry(ref) == "2025-01-17"


class TestResolveExpiry:
    def test_dispatches_zero_dte(self) -> None:
        ref = datetime(2024, 3, 13, 10, 0, tzinfo=UTC)
        assert resolve_expiry(ExpiryCategory.ZERO_DTE, ref) == "2024-03-13"

    def test_dispatches_weekly(self) -> None:
        ref = datetime(2024, 3, 13, 10, 0, tzinfo=UTC)
        assert resolve_expiry(ExpiryCategory.WEEKLY, ref) == "2024-03-15"

    def test_dispatches_monthly(self) -> None:
        ref = datetime(2024, 3, 1, 10, 0, tzinfo=UTC)
        assert resolve_expiry(ExpiryCategory.MONTHLY, ref) == "2024-03-15"
