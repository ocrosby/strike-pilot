"""Alert service adapters.

Implements the AlertService port for announcing actionable trade recommendations
to various output channels. Only SpreadRecommendation results (not NoTradeSignal)
ever reach these adapters — the filtering happens in the use case layer.
"""

from __future__ import annotations

import logging

from strike_pilot.domain.models import MarketBias, SpreadRecommendation


class LoggingAlertService:
    """Emits trade alerts via Python's standard logging framework.

    Suitable for production use where alerts should flow through existing
    log aggregation infrastructure (e.g., CloudWatch, Datadog, syslog).
    """

    def __init__(self, logger_name: str = "strike_pilot.alerts") -> None:
        self._logger = logging.getLogger(logger_name)

    def alert(self, bias: MarketBias, recommendation: SpreadRecommendation) -> None:
        """Log the trade recommendation at INFO level.

        Args:
            bias: The market bias that drove the recommendation.
            recommendation: The actionable spread trade to announce.
        """
        self._logger.info(
            "TRADE ALERT | %s %s | short: %.1f %s buy %.1f | "
            "credit: $%.2f | max loss: $%.2f | R/R: %.1f | bias: %s (%.0f%%)",
            recommendation.spread_type.value,
            recommendation.short_leg.expiry,
            recommendation.short_leg.strike,
            recommendation.short_leg.option_type.upper(),
            recommendation.long_leg.strike,
            recommendation.net_credit,
            recommendation.max_loss,
            recommendation.risk_reward_ratio,
            bias.direction.value,
            bias.confidence.value * 100,
        )


class ConsoleAlertService:
    """Prints trade alerts to stdout in a human-readable format.

    Useful for local development, demos, and interactive CLI sessions where
    a visually distinct alert is preferable to standard output lines.
    """

    def alert(self, bias: MarketBias, recommendation: SpreadRecommendation) -> None:
        """Print a formatted trade alert to stdout.

        Args:
            bias: The market bias that drove the recommendation.
            recommendation: The actionable spread trade to announce.
        """
        separator = "=" * 50
        print(separator)
        print("*** TRADE ALERT ***")
        print(f"  Strategy   : {recommendation.spread_type.value}")
        print(f"  Expiry     : {recommendation.short_leg.expiry}")
        print(
            f"  Spread     : sell {recommendation.short_leg.strike:.1f} "
            f"{recommendation.short_leg.option_type.upper()} / "
            f"buy {recommendation.long_leg.strike:.1f} "
            f"{recommendation.long_leg.option_type.upper()}"
        )
        print(f"  Net Credit : ${recommendation.net_credit:.2f}")
        print(f"  Max Loss   : ${recommendation.max_loss:.2f}")
        print(f"  R/R Ratio  : {recommendation.risk_reward_ratio:.1f}")
        print(f"  Bias       : {bias.direction.value} ({bias.confidence.value:.0%})")
        print(separator)
