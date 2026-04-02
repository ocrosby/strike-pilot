"""Domain policies for trade validation and filtering.

Policies are pure functions/objects that encode business rules.
They have no infrastructure dependencies.
"""

from __future__ import annotations

from strike_pilot.domain.models import (
    MarketBias,
    RiskParameters,
    SpreadRecommendation,
)


def is_confidence_sufficient(bias: MarketBias, risk_params: RiskParameters) -> bool:
    """Check if the bias confidence meets the minimum threshold."""
    return bias.confidence.value >= risk_params.min_confidence_threshold


def is_credit_adequate(recommendation: SpreadRecommendation, risk_params: RiskParameters) -> bool:
    """Check if the net credit meets the minimum required."""
    return recommendation.net_credit >= risk_params.min_credit_dollars


def is_max_loss_within_limit(
    recommendation: SpreadRecommendation, risk_params: RiskParameters
) -> bool:
    """Check if max loss does not exceed the allowed maximum."""
    return recommendation.max_loss <= risk_params.max_loss_dollars


def is_spread_width_valid(
    recommendation: SpreadRecommendation, risk_params: RiskParameters
) -> bool:
    """Check if spread width is within the configured maximum."""
    return recommendation.spread_width <= risk_params.max_spread_width


def passes_all_risk_checks(
    recommendation: SpreadRecommendation,
    bias: MarketBias,
    risk_params: RiskParameters,
) -> bool:
    """Return True only if ALL risk policy checks pass."""
    return (
        is_confidence_sufficient(bias, risk_params)
        and is_credit_adequate(recommendation, risk_params)
        and is_max_loss_within_limit(recommendation, risk_params)
        and is_spread_width_valid(recommendation, risk_params)
    )
