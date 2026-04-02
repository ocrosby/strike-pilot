"""Pydantic request and response models for the Strike Pilot HTTP API.

These models define the JSON contract for the API surface. They are kept
separate from the domain models so that serialisation concerns (field names,
defaults, validation messages) don't bleed into the domain layer.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RiskParamsRequest(BaseModel):
    """Risk constraints forwarded to the domain's RiskParameters."""

    max_loss_dollars: float = Field(default=1000.0, gt=0, description="Maximum loss in dollars.")
    min_credit_dollars: float = Field(
        default=50.0, gt=0, description="Minimum net credit in dollars."
    )
    max_spread_width: float = Field(default=10.0, gt=0, description="Maximum spread width.")
    min_confidence_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum bias confidence (0-1)."
    )


class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    symbol: str = Field(default="SPX", description="Market symbol to analyze.")
    expiry: str | None = Field(default=None, description="Explicit expiry date (YYYY-MM-DD).")
    strategy: Literal["delta", "pop", "risk-reward"] = Field(
        default="delta",
        description="Strike selection strategy.",
    )
    data_source: Literal["static", "live"] = Field(
        default="static",
        description="Market data source.",
    )
    risk_params: RiskParamsRequest = Field(default_factory=RiskParamsRequest)
    spread_width: float = Field(default=10.0, gt=0, description="Spread width (points).")
    target_pop: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Target PoP. Used when strategy='pop'."
    )
    target_rr: float = Field(
        default=5.0, gt=0, description="Target R/R ratio. Used when strategy='risk-reward'."
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class BiasResponse(BaseModel):
    """Serialised MarketBias."""

    direction: str
    confidence: float
    rationale: str


class SpreadLegResponse(BaseModel):
    """Serialised SpreadLeg."""

    strike: float
    expiry: str
    option_type: str
    action: str
    premium: float


class SpreadRecommendationResponse(BaseModel):
    """Serialised SpreadRecommendation — an actionable trade."""

    action: Literal["trade"]
    spread_type: str
    short_leg: SpreadLegResponse
    long_leg: SpreadLegResponse
    net_credit: float
    max_loss: float
    risk_reward_ratio: float
    rationale: str


class NoTradeResponse(BaseModel):
    """Serialised NoTradeSignal — no trade recommended."""

    action: Literal["no_trade"]
    reason: str


RecommendationResponse = Annotated[
    SpreadRecommendationResponse | NoTradeResponse,
    Field(discriminator="action"),
]


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze."""

    bias: BiasResponse
    recommendation: RecommendationResponse
