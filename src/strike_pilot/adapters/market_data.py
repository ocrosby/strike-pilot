"""Market data adapter implementations.

Provides mock/static market data for development and testing.
In production, replace with live data provider adapters.
"""

from __future__ import annotations

from typing import ClassVar

from strike_pilot.domain.models import MarketSnapshot


class StaticMarketDataAdapter:
    """Adapter that returns static/hardcoded SPX market data.

    Useful for development, demos, and testing.
    """

    _STATIC_DATA: ClassVar[dict[str, dict[str, float | str]]] = {
        "SPX": {
            "price": 5250.0,
            "open_price": 5220.0,
            "high_price": 5265.0,
            "low_price": 5210.0,
            "vix": 16.5,
            "sma_20": 5200.0,
            "sma_50": 5150.0,
            "rsi_14": 58.0,
            "timestamp": "2024-01-19T10:30:00",
        }
    }

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Return a static market snapshot for the given symbol."""
        data = self._STATIC_DATA.get(symbol.upper())
        if data is None:
            return MarketSnapshot(
                symbol=symbol,
                price=5000.0,
                open_price=5000.0,
                high_price=5010.0,
                low_price=4990.0,
                vix=18.0,
                timestamp="2024-01-19T10:30:00",
            )
        return MarketSnapshot(
            symbol=symbol,
            price=float(data["price"]),
            open_price=float(data["open_price"]),
            high_price=float(data["high_price"]),
            low_price=float(data["low_price"]),
            vix=float(data["vix"]),
            timestamp=str(data["timestamp"]),
            sma_20=float(data.get("sma_20", 0.0)),
            sma_50=float(data.get("sma_50", 0.0)),
            rsi_14=float(data.get("rsi_14", 50.0)),
        )
