"""Static historical data adapter for deterministic testing and demos.

Provides a fixed week of SPX data (Mon 2024-01-15 through Fri 2024-01-19)
with a mix of bullish and neutral signals, plus a second week's closing
price for expiry simulation.
"""

from __future__ import annotations

from strike_pilot.domain.models import MarketSnapshot

_SNAPSHOTS: list[MarketSnapshot] = [
    MarketSnapshot(
        symbol="SPX",
        price=5250.0,
        open_price=5220.0,
        high_price=5265.0,
        low_price=5210.0,
        vix=16.5,
        timestamp="2024-01-15T16:00:00",
        sma_20=5200.0,
        sma_50=5150.0,
        rsi_14=58.0,
        iv_rank=0.62,
        iv_percentile=0.55,
    ),
    MarketSnapshot(
        symbol="SPX",
        price=5260.0,
        open_price=5255.0,
        high_price=5275.0,
        low_price=5245.0,
        vix=15.8,
        timestamp="2024-01-16T16:00:00",
        sma_20=5205.0,
        sma_50=5152.0,
        rsi_14=61.0,
        iv_rank=0.58,
        iv_percentile=0.52,
    ),
    MarketSnapshot(
        symbol="SPX",
        price=5245.0,
        open_price=5260.0,
        high_price=5268.0,
        low_price=5240.0,
        vix=17.2,
        timestamp="2024-01-17T16:00:00",
        sma_20=5208.0,
        sma_50=5154.0,
        rsi_14=52.0,
        iv_rank=0.55,
        iv_percentile=0.50,
    ),
    MarketSnapshot(
        symbol="SPX",
        price=5270.0,
        open_price=5248.0,
        high_price=5280.0,
        low_price=5242.0,
        vix=15.5,
        timestamp="2024-01-18T16:00:00",
        sma_20=5210.0,
        sma_50=5156.0,
        rsi_14=64.0,
        iv_rank=0.60,
        iv_percentile=0.54,
    ),
    MarketSnapshot(
        symbol="SPX",
        price=5280.0,
        open_price=5272.0,
        high_price=5290.0,
        low_price=5268.0,
        vix=15.0,
        timestamp="2024-01-19T16:00:00",
        sma_20=5215.0,
        sma_50=5158.0,
        rsi_14=66.0,
        iv_rank=0.59,
        iv_percentile=0.53,
    ),
]

_CLOSE_PRICES: dict[str, dict[str, float]] = {
    "SPX": {
        "2024-01-15": 5250.0,
        "2024-01-16": 5260.0,
        "2024-01-17": 5245.0,
        "2024-01-18": 5270.0,
        "2024-01-19": 5280.0,
        "2024-01-22": 5290.0,
        "2024-01-23": 5295.0,
        "2024-01-24": 5300.0,
        "2024-01-25": 5305.0,
        "2024-01-26": 5310.0,
    }
}


class StaticHistoricalDataAdapter:
    """Returns fixed SPX daily snapshots for development and testing."""

    def get_snapshots(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[MarketSnapshot]:
        """Return snapshots within [start_date, end_date] for symbol.

        Args:
            symbol: Ignored; always returns SPX data.
            start_date: ISO date — inclusive lower bound.
            end_date: ISO date — inclusive upper bound.

        Returns:
            Filtered snapshots sorted by timestamp.
        """
        return [s for s in _SNAPSHOTS if start_date <= s.timestamp[:10] <= end_date]

    def get_close_price(self, symbol: str, date: str) -> float | None:
        """Return the static closing price for symbol on date.

        Args:
            symbol: Ignored; always returns SPX data.
            date: ISO date string.

        Returns:
            Closing price, or None if not in the static dataset.
        """
        return _CLOSE_PRICES.get("SPX", {}).get(date)
