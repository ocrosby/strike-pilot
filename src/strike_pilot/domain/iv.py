"""Implied volatility rank and percentile computations.

Pure functions for computing IV rank and IV percentile from historical data.
These are domain calculations with no infrastructure dependencies.
"""

from __future__ import annotations


def compute_iv_rank(current_iv: float, low_iv: float, high_iv: float) -> float:
    """Compute IV rank as a value between 0.0 and 1.0.

    IV Rank = (Current IV - 52-week Low IV) / (52-week High IV - 52-week Low IV)

    Returns 0.0 when high equals low (no range).
    """
    if high_iv <= low_iv:
        return 0.0
    return max(0.0, min(1.0, (current_iv - low_iv) / (high_iv - low_iv)))


def compute_iv_percentile(current_iv: float, historical_ivs: list[float]) -> float:
    """Compute IV percentile as a value between 0.0 and 1.0.

    IV Percentile = fraction of days in the lookback period where IV was below current IV.

    Returns 0.0 when the history is empty.
    """
    if not historical_ivs:
        return 0.0
    below_count = sum(1 for iv in historical_ivs if iv < current_iv)
    return below_count / len(historical_ivs)
