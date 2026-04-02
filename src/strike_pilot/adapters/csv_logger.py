"""CSV recommendation logger adapter.

Appends bias and recommendation results to a CSV file for persistence.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from strike_pilot.domain.models import (
    MarketBias,
    NoTradeSignal,
    SpreadRecommendation,
)

_FIELDNAMES = [
    "timestamp",
    "bias_direction",
    "bias_confidence",
    "bias_rationale",
    "action",
    "spread_type",
    "short_strike",
    "long_strike",
    "expiry",
    "net_credit",
    "max_loss",
    "risk_reward_ratio",
    "rationale",
]


class CsvRecommendationLogger:
    """Appends analysis results as rows in a CSV file."""

    def __init__(self, path: Path, clock_now: datetime | None = None) -> None:
        self._path = path
        self._clock_now = clock_now

    def log(
        self,
        bias: MarketBias,
        result: SpreadRecommendation | NoTradeSignal,
    ) -> None:
        """Append one row to the CSV file, creating headers if the file is new."""
        write_header = not self._path.exists() or self._path.stat().st_size == 0
        timestamp = (self._clock_now or datetime.now()).isoformat()

        row = self._build_row(timestamp, bias, result)

        with self._path.open("a", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

    @staticmethod
    def _build_row(
        timestamp: str,
        bias: MarketBias,
        result: SpreadRecommendation | NoTradeSignal,
    ) -> dict[str, object]:
        base: dict[str, object] = {
            "timestamp": timestamp,
            "bias_direction": bias.direction.value,
            "bias_confidence": bias.confidence.value,
            "bias_rationale": bias.rationale,
        }
        if isinstance(result, NoTradeSignal):
            base.update(
                {
                    "action": "no_trade",
                    "spread_type": "",
                    "short_strike": "",
                    "long_strike": "",
                    "expiry": "",
                    "net_credit": "",
                    "max_loss": "",
                    "risk_reward_ratio": "",
                    "rationale": result.reason,
                }
            )
        else:
            base.update(
                {
                    "action": "trade",
                    "spread_type": result.spread_type.value,
                    "short_strike": result.short_leg.strike,
                    "long_strike": result.long_leg.strike,
                    "expiry": result.short_leg.expiry,
                    "net_credit": result.net_credit,
                    "max_loss": result.max_loss,
                    "risk_reward_ratio": round(result.risk_reward_ratio, 4),
                    "rationale": result.rationale,
                }
            )
        return base
