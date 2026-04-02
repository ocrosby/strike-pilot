"""Expiry date resolution for different time-frame categories.

Pure functions that compute concrete expiry dates from a reference datetime.
No I/O dependencies.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from strike_pilot.domain.models import ExpiryCategory

_ISO_FMT = "%Y-%m-%d"


def resolve_expiry(category: ExpiryCategory, reference: datetime) -> str:
    """Resolve an expiry category to a concrete ISO date string."""
    if category == ExpiryCategory.ZERO_DTE:
        return zero_dte_expiry(reference)
    if category == ExpiryCategory.WEEKLY:
        return weekly_expiry(reference)
    return monthly_expiry(reference)


def zero_dte_expiry(reference: datetime) -> str:
    """Return today's date as the 0DTE expiry."""
    return reference.strftime(_ISO_FMT)


def weekly_expiry(reference: datetime) -> str:
    """Return the Friday of the current week, or next Friday on weekends."""
    weekday = reference.weekday()  # 0=Mon ... 6=Sun
    if weekday <= 4:
        # Mon-Fri: this week's Friday
        days_to_friday = 4 - weekday
        friday = reference + timedelta(days=days_to_friday)
    else:
        # Sat(5) or Sun(6): next week's Friday
        days_to_friday = 4 + (7 - weekday)
        friday = reference + timedelta(days=days_to_friday)
    return friday.strftime(_ISO_FMT)


def monthly_expiry(reference: datetime) -> str:
    """Return the third Friday of the current or next month.

    If the third Friday of the current month has already passed,
    returns the third Friday of the following month.
    """
    third_friday = _third_friday_of_month(reference.year, reference.month)
    if reference.date() > third_friday:
        # Roll to next month
        if reference.month == 12:
            third_friday = _third_friday_of_month(reference.year + 1, 1)
        else:
            third_friday = _third_friday_of_month(reference.year, reference.month + 1)
    return third_friday.strftime(_ISO_FMT)


def _third_friday_of_month(year: int, month: int) -> date:
    """Compute the date of the third Friday of a given month."""
    # First day of the month
    first_day_weekday = calendar.weekday(year, month, 1)  # 0=Mon ... 6=Sun
    # Days until first Friday (Friday = 4)
    days_to_first_friday = (4 - first_day_weekday) % 7
    first_friday = 1 + days_to_first_friday
    third_friday_day = first_friday + 14
    return date(year, month, third_friday_day)
