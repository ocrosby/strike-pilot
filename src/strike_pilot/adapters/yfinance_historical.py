"""Historical market data adapter backed by yfinance.

Fetches daily OHLCV data for a date range and reconstructs MarketSnapshot
objects with rolling RSI-14, SMA-20, and SMA-50 indicators. VIX is fetched
as a separate ticker and aligned by date.

Note: yfinance does not provide historical options chain data. Use
SyntheticOptionsChainAdapter to generate approximate chains from these
snapshots for backtesting purposes.
"""

from __future__ import annotations

from datetime import date, timedelta

import yfinance as yf

from strike_pilot.adapters.yfinance_market_data import _compute_rsi, _yfinance_symbol
from strike_pilot.domain.models import MarketSnapshot

# Extra history needed before start_date to warm up SMA-50 and RSI-14
_WARMUP_DAYS = 100


class YFinanceHistoricalDataAdapter:
    """Fetches daily historical SPX data and closing prices from Yahoo Finance."""

    def get_snapshots(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[MarketSnapshot]:
        """Fetch daily snapshots between start_date and end_date inclusive.

        Prefetches _WARMUP_DAYS of additional history before start_date so
        that SMA-50 and RSI-14 are fully populated from the first snapshot.

        Args:
            symbol: Market symbol (e.g. "SPX").
            start_date: ISO date string (inclusive).
            end_date: ISO date string (inclusive, yfinance end is exclusive so we add 1 day).

        Returns:
            Snapshots sorted by date ascending.
        """
        yf_symbol = _yfinance_symbol(symbol)
        extended_start = (date.fromisoformat(start_date) - timedelta(days=_WARMUP_DAYS)).isoformat()
        fetch_end = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

        history = yf.download(
            yf_symbol, start=extended_start, end=fetch_end, auto_adjust=True, progress=False
        )
        vix_history = yf.download(
            "^VIX", start=extended_start, end=fetch_end, auto_adjust=True, progress=False
        )

        if history.empty:
            return []

        snapshots: list[MarketSnapshot] = []
        for i, idx in enumerate(history.index):
            row_date = idx.strftime("%Y-%m-%d")
            if row_date < start_date:
                continue  # skip warm-up prefix

            row = history.iloc[i]
            closes = history["Close"].iloc[: i + 1]

            sma_20 = float(closes.tail(20).mean())
            sma_50 = float(closes.tail(50).mean())
            rsi_14 = _compute_rsi(closes, period=14)

            vix_up_to = vix_history[vix_history.index <= idx]
            vix = float(vix_up_to["Close"].iloc[-1]) if not vix_up_to.empty else 20.0

            snapshots.append(
                MarketSnapshot(
                    symbol=symbol,
                    price=float(row["Close"]),
                    open_price=float(row["Open"]),
                    high_price=float(row["High"]),
                    low_price=float(row["Low"]),
                    vix=vix,
                    timestamp=f"{row_date}T16:00:00",
                    sma_20=sma_20,
                    sma_50=sma_50,
                    rsi_14=rsi_14,
                )
            )

        return snapshots

    def get_close_price(self, symbol: str, date_str: str) -> float | None:
        """Fetch the closing price for symbol on a specific date.

        Args:
            symbol: Market symbol.
            date_str: ISO date string.

        Returns:
            Closing price, or None if the date is a non-trading day or
            outside the available data range.
        """
        yf_symbol = _yfinance_symbol(symbol)
        fetch_end = (date.fromisoformat(date_str) + timedelta(days=1)).isoformat()
        history = yf.download(
            yf_symbol, start=date_str, end=fetch_end, auto_adjust=True, progress=False
        )
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])
