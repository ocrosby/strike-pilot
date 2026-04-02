"""Port interfaces (Protocols) for all external system boundaries.

These define the contracts that adapters must satisfy.
All infrastructure adapters implement these protocols.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from strike_pilot.domain.models import (
    ExpiryRecommendation,
    MarketBias,
    MarketSnapshot,
    NoTradeSignal,
    OptionsChain,
    SpreadRecommendation,
)


@runtime_checkable
class MarketDataProvider(Protocol):
    """Port for retrieving market snapshot data."""

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        """Retrieve the latest market snapshot for the given symbol."""
        ...


@runtime_checkable
class OptionsChainProvider(Protocol):
    """Port for retrieving options chain data."""

    def get_chain(self, symbol: str, expiry: str) -> OptionsChain:
        """Retrieve the options chain for a symbol and expiry date."""
        ...


@runtime_checkable
class SignalProvider(Protocol):
    """Port for retrieving additional market signals or indicators."""

    def get_signals(self, symbol: str) -> dict[str, float]:
        """Retrieve a dictionary of named signals for the given symbol."""
        ...


@runtime_checkable
class OutputPresenter(Protocol):
    """Port for presenting analysis results to the user."""

    def present_bias(self, bias: MarketBias) -> None:
        """Present the market bias."""
        ...

    def present_recommendation(self, result: SpreadRecommendation | NoTradeSignal) -> None:
        """Present a spread recommendation or no-trade signal."""
        ...

    def present_multi_recommendations(
        self,
        bias: MarketBias,
        recommendations: list[ExpiryRecommendation],
    ) -> None:
        """Present bias and recommendations for multiple expiry categories."""
        ...


@runtime_checkable
class RecommendationLogger(Protocol):
    """Port for persisting analysis results to durable storage."""

    def log(
        self,
        bias: MarketBias,
        result: SpreadRecommendation | NoTradeSignal,
    ) -> None:
        """Log a bias and recommendation/no-trade result."""
        ...


@runtime_checkable
class Clock(Protocol):
    """Port for time/clock abstraction."""

    def now(self) -> datetime:
        """Return the current datetime."""
        ...


@runtime_checkable
class HistoricalDataProvider(Protocol):
    """Port for fetching historical market data for backtesting."""

    def get_snapshots(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> list[MarketSnapshot]:
        """Return daily snapshots between start_date and end_date (inclusive).

        Args:
            symbol: Market symbol (e.g. "SPX").
            start_date: ISO date string for the first day.
            end_date: ISO date string for the last day.

        Returns:
            Snapshots sorted by timestamp ascending.
        """
        ...

    def get_close_price(self, symbol: str, date: str) -> float | None:
        """Return the closing price for symbol on date, or None if unavailable.

        Args:
            symbol: Market symbol.
            date: ISO date string.

        Returns:
            Closing price, or None when the date is a non-trading day or
            outside the available data range.
        """
        ...


@runtime_checkable
class AlertService(Protocol):
    """Port for sending trade alerts to external channels.

    Only called when a SpreadRecommendation is produced — NoTradeSignal
    results are intentionally excluded so downstream channels receive only
    actionable signals.
    """

    def alert(self, bias: MarketBias, recommendation: SpreadRecommendation) -> None:
        """Send an alert for the given trade recommendation.

        Args:
            bias: The market bias that drove the recommendation.
            recommendation: The actionable spread trade to announce.
        """
        ...
