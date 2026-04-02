"""Clock adapter implementations."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Clock adapter using the system time."""

    def now(self) -> datetime:
        """Return current UTC time."""
        return datetime.now(tz=UTC)


class FixedClock:
    """Clock adapter returning a fixed time, useful for testing."""

    def __init__(self, fixed_time: datetime) -> None:
        self._time = fixed_time

    def now(self) -> datetime:
        """Return the fixed time."""
        return self._time
