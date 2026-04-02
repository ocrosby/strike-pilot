"""Presenter adapter implementations.

Adapters for formatting and outputting analysis results.
"""

from __future__ import annotations

import json

from strike_pilot.domain.models import MarketBias, NoTradeSignal, SpreadRecommendation


class ConsolePresenter:
    """Presents analysis results to stdout in human-readable format."""

    def present_bias(self, bias: MarketBias) -> None:
        """Print bias direction and confidence to stdout."""
        print(f"\n{'='*50}")
        print("SPX INTRADAY BIAS ANALYSIS")
        print(f"{'='*50}")
        print(f"Direction  : {bias.direction.value.upper()}")
        print(f"Confidence : {bias.confidence.value:.1%}")
        print(f"Rationale  : {bias.rationale}")
        print(f"{'='*50}")

    def present_recommendation(
        self, result: SpreadRecommendation | NoTradeSignal
    ) -> None:
        """Print spread recommendation or no-trade signal to stdout."""
        if isinstance(result, NoTradeSignal):
            print("\nRECOMMENDATION: NO TRADE")
            print(f"Reason: {result.reason}")
        else:
            print("\nRECOMMENDATION: SPREAD TRADE")
            print(f"  Type       : {result.spread_type.value.replace('_', ' ').title()}")
            print(
                f"  Short Leg  : {result.short_leg.action.upper()} "
                f"{result.short_leg.strike} {result.short_leg.option_type.upper()}"
            )
            print(
                f"  Long Leg   : {result.long_leg.action.upper()} "
                f"{result.long_leg.strike} {result.long_leg.option_type.upper()}"
            )
            print(f"  Expiry     : {result.short_leg.expiry}")
            print(f"  Net Credit : ${result.net_credit:.2f}")
            print(f"  Max Loss   : ${result.max_loss:.2f}")
            print(f"  R/R Ratio  : {result.risk_reward_ratio:.2f}")
            print(f"  Rationale  : {result.rationale}")
        print()


class JsonPresenter:
    """Presents analysis results as JSON to stdout."""

    def present_bias(self, bias: MarketBias) -> None:
        """Print bias as JSON to stdout."""
        data = {
            "bias": {
                "direction": bias.direction.value,
                "confidence": bias.confidence.value,
                "rationale": bias.rationale,
            }
        }
        print(json.dumps(data, indent=2))

    def present_recommendation(
        self, result: SpreadRecommendation | NoTradeSignal
    ) -> None:
        """Print recommendation as JSON to stdout."""
        if isinstance(result, NoTradeSignal):
            data: dict = {
                "recommendation": {
                    "action": "no_trade",
                    "reason": result.reason,
                }
            }
        else:
            data = {
                "recommendation": {
                    "action": "trade",
                    "spread_type": result.spread_type.value,
                    "short_leg": {
                        "strike": result.short_leg.strike,
                        "expiry": result.short_leg.expiry,
                        "option_type": result.short_leg.option_type,
                        "action": result.short_leg.action,
                        "premium": result.short_leg.premium,
                    },
                    "long_leg": {
                        "strike": result.long_leg.strike,
                        "expiry": result.long_leg.expiry,
                        "option_type": result.long_leg.option_type,
                        "action": result.long_leg.action,
                        "premium": result.long_leg.premium,
                    },
                    "net_credit": result.net_credit,
                    "max_loss": result.max_loss,
                    "risk_reward_ratio": result.risk_reward_ratio,
                    "rationale": result.rationale,
                }
            }
        print(json.dumps(data, indent=2))
