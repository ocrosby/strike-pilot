"""Core domain models for Strike Pilot.

These are pure data/value types with no infrastructure dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BiasDirection(StrEnum):
    """Directional bias for intraday SPX movement."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SpreadType(StrEnum):
    """Type of credit spread."""

    BULL_PUT = "bull_put"
    BEAR_CALL = "bear_call"


@dataclass(frozen=True)
class ConfidenceScore:
    """A normalized confidence score between 0.0 and 1.0."""

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"ConfidenceScore must be between 0.0 and 1.0, got {self.value}")

    def __float__(self) -> float:
        return self.value

    @property
    def is_high(self) -> bool:
        """Returns True if confidence is >= 0.7."""
        return self.value >= 0.7

    @property
    def is_low(self) -> bool:
        """Returns True if confidence is < 0.4."""
        return self.value < 0.4


@dataclass(frozen=True)
class MarketBias:
    """Represents the intraday directional bias for SPX."""

    direction: BiasDirection
    confidence: ConfidenceScore
    rationale: str = ""

    @classmethod
    def neutral(cls, rationale: str = "Insufficient signal") -> MarketBias:
        """Create a neutral bias with a default low confidence."""
        return cls(
            direction=BiasDirection.NEUTRAL,
            confidence=ConfidenceScore(0.5),
            rationale=rationale,
        )


@dataclass(frozen=True)
class RiskParameters:
    """Risk constraints for spread recommendations."""

    max_loss_dollars: float
    min_credit_dollars: float
    max_spread_width: float
    min_confidence_threshold: float = 0.6

    def __post_init__(self) -> None:
        if self.max_loss_dollars <= 0:
            raise ValueError("max_loss_dollars must be positive")
        if self.min_credit_dollars <= 0:
            raise ValueError("min_credit_dollars must be positive")
        if self.max_spread_width <= 0:
            raise ValueError("max_spread_width must be positive")
        if not (0.0 <= self.min_confidence_threshold <= 1.0):
            raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")


@dataclass(frozen=True)
class SpreadLeg:
    """A single leg in a credit spread."""

    strike: float
    expiry: str  # ISO date string e.g. "2024-01-19"
    option_type: str  # "call" or "put"
    action: str  # "buy" or "sell"
    premium: float


@dataclass(frozen=True)
class SpreadRecommendation:
    """A recommended credit spread trade or a no-trade signal."""

    spread_type: SpreadType
    short_leg: SpreadLeg
    long_leg: SpreadLeg
    net_credit: float
    max_loss: float
    bias: MarketBias
    rationale: str = ""

    @property
    def spread_width(self) -> float:
        """Width of the spread in points."""
        return abs(self.long_leg.strike - self.short_leg.strike)

    @property
    def risk_reward_ratio(self) -> float:
        """Ratio of max loss to net credit."""
        if self.net_credit == 0:
            return float("inf")
        return self.max_loss / self.net_credit


@dataclass(frozen=True)
class NoTradeSignal:
    """Represents a decision to not recommend a trade."""

    reason: str
    bias: MarketBias | None = None


@dataclass
class MarketSnapshot:
    """Point-in-time market data for SPX analysis."""

    symbol: str
    price: float
    open_price: float
    high_price: float
    low_price: float
    vix: float
    timestamp: str  # ISO datetime string
    sma_20: float = 0.0
    sma_50: float = 0.0
    rsi_14: float = 50.0
    additional_signals: dict[str, float] = field(default_factory=dict)


@dataclass
class OptionsChain:
    """Simplified options chain data for SPX."""

    symbol: str
    expiry: str
    underlying_price: float
    strikes: list[float] = field(default_factory=list)
    call_premiums: dict[float, float] = field(default_factory=dict)
    put_premiums: dict[float, float] = field(default_factory=dict)
    call_deltas: dict[float, float] = field(default_factory=dict)
    put_deltas: dict[float, float] = field(default_factory=dict)
