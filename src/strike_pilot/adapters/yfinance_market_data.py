"""Live market data adapter backed by yfinance.

Fetches real-time SPX (and other index/equity) snapshots including
price, OHLC, VIX, SMA-20, SMA-50, and RSI-14.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import yfinance as yf

from strike_pilot.domain.models import MarketSnapshot

# Symbols that require the '^' prefix in yfinance
_INDEX_PREFIXES: frozenset[str] = frozenset({"SPX", "NDX", "RUT", "DJI", "VIX", "GSPC"})


def _yfinance_symbol(symbol: str) -> str:
    """Map a bare index symbol to its yfinance ticker format."""
    upper = symbol.upper()
    if upper in _INDEX_PREFIXES:
        return f"^{upper}"
    return symbol


def _compute_iv_rank(vix_series: pd.Series) -> float:
    """Compute IV rank as the position of the current VIX within the 52-week range.

    IV rank = (current - 52w_low) / (52w_high - 52w_low).
    Returns 0.0 when the range is zero (constant VIX). Result is clamped to [0.0, 1.0].
    """
    if vix_series.empty:
        return 0.0
    current = float(vix_series.iloc[-1])
    low = float(vix_series.min())
    high = float(vix_series.max())
    if high == low:
        return 0.0
    return float(min(max((current - low) / (high - low), 0.0), 1.0))


def _compute_iv_percentile(vix_series: pd.Series) -> float:
    """Compute IV percentile as the fraction of historical days with VIX below current.

    Returns a value in [0.0, 1.0]. Returns 0.0 for an empty or single-element series.
    """
    if len(vix_series) < 2:
        return 0.0
    current = float(vix_series.iloc[-1])
    historical = vix_series.iloc[:-1]
    return float((historical < current).sum() / len(historical))


def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    """Compute RSI using simple mean of gains and losses over the last period+1 bars.

    Returns a value in [0, 100]. Returns 100.0 when there are no down-moves.
    """
    delta = closes.diff().dropna()
    recent = delta.tail(period)
    gains = recent.clip(lower=0)
    losses = (-recent).clip(lower=0)
    avg_gain = gains.mean()
    avg_loss = losses.mean()
    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - 100.0 / (1.0 + rs))


class YFinanceMarketDataAdapter:
    """Adapter that fetches live market data from Yahoo Finance via yfinance.

    Retrieves 3 months of daily history to support SMA-50 calculation.
    VIX is fetched separately from the ^VIX ticker.
    """

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Fetch a live market snapshot for the given symbol.

        Args:
            symbol: Market symbol (e.g. "SPX", "AAPL"). Index symbols are
                automatically prefixed with '^' for yfinance compatibility.

        Returns:
            A populated MarketSnapshot with price, OHLC, VIX, SMA-20, SMA-50,
            and RSI-14 fields.

        Raises:
            ValueError: If yfinance returns no data for the symbol.
        """
        yf_symbol = _yfinance_symbol(symbol)
        history = yf.Ticker(yf_symbol).history(period="3mo")

        if history.empty:
            raise ValueError(f"No data available for {symbol}")

        latest = history.iloc[-1]
        closes = history["Close"]

        sma_20 = float(closes.tail(20).mean())
        sma_50 = float(closes.tail(50).mean())
        rsi_14 = _compute_rsi(closes, period=14)

        vix_history = yf.Ticker("^VIX").history(period="1y")
        vix_closes = vix_history["Close"] if not vix_history.empty else pd.Series(dtype=float)
        vix = float(vix_closes.iloc[-1]) if not vix_closes.empty else 20.0
        iv_rank = _compute_iv_rank(vix_closes)
        iv_percentile = _compute_iv_percentile(vix_closes)

        return MarketSnapshot(
            symbol=symbol,
            price=float(latest["Close"]),
            open_price=float(latest["Open"]),
            high_price=float(latest["High"]),
            low_price=float(latest["Low"]),
            vix=vix,
            timestamp=datetime.now(tz=UTC).isoformat(),
            sma_20=sma_20,
            sma_50=sma_50,
            rsi_14=rsi_14,
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
        )
