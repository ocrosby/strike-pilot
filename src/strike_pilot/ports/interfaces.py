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
