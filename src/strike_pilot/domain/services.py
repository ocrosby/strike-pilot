"""Domain services for bias analysis and spread recommendation.

These are pure domain services that use Strategy pattern for pluggable
analysis and scoring logic. They depend on domain abstractions only.
"""

from __future__ import annotations

from typing import Protocol

from strike_pilot.domain.models import (
    BiasDirection,
    ConfidenceScore,
    MarketBias,
    MarketSnapshot,
    NoTradeSignal,
    OptionsChain,
    RiskParameters,
    SpreadLeg,
    SpreadRecommendation,
    SpreadType,
)
from strike_pilot.domain.policies import passes_all_risk_checks


class BiasStrategy(Protocol):
    """Strategy for determining intraday directional bias."""

    def analyze(self, snapshot: MarketSnapshot) -> MarketBias:
        """Analyze market snapshot and return bias."""
        ...


class StrikeSelectionStrategy(Protocol):
    """Strategy for selecting spread strikes."""

    def select_strikes(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Select strikes and return a recommendation or no-trade signal."""
        ...


class SimpleMomentumBiasStrategy:
    """Determines bias using price momentum and RSI signals.

    This is a simple placeholder strategy demonstrating the architecture.
    """

    def analyze(self, snapshot: MarketSnapshot) -> MarketBias:
        """Analyze price momentum, RSI, and IV signals to determine bias."""
        signals: list[float] = []

        # Price vs open: normalize so a 1% move = 0.5, 2% = 1.0
        price_change_pct = (snapshot.price - snapshot.open_price) / snapshot.open_price
        signals.append(min(1.0, max(-1.0, price_change_pct * 50)))

        # RSI signal: normalize so RSI 80 = 0.6 bullish, RSI 20 = 0.6 bearish
        rsi_signal = min(1.0, max(-1.0, (snapshot.rsi_14 - 50.0) / 25.0))
        signals.append(rsi_signal)

        # SMA signal: price above 20-SMA is bullish; normalize so 1% above = 0.5
        if snapshot.sma_20 > 0:
            sma_deviation = (snapshot.price - snapshot.sma_20) / snapshot.sma_20 * 50
            sma_signal = min(1.0, max(-1.0, sma_deviation))
            signals.append(sma_signal)

        # VIX: high VIX suppresses confidence
        vix_penalty = max(0.0, (snapshot.vix - 20.0) / 40.0)

        avg_signal = sum(signals) / len(signals) if signals else 0.0

        # Confidence = blend of signal alignment and signal strength
        aligned_count = sum(1 for s in signals if (s > 0) == (avg_signal > 0) and s != 0)
        alignment_ratio = aligned_count / len(signals) if signals else 0.5
        strength = min(1.0, abs(avg_signal))
        raw_confidence = alignment_ratio * 0.5 + strength * 0.5
        adjusted_confidence = max(0.0, raw_confidence - vix_penalty)

        # IV rank/percentile adjustment: high IV favours premium selling
        iv_bonus = self._iv_confidence_adjustment(snapshot)
        adjusted_confidence = adjusted_confidence + iv_bonus

        # Build rationale parts
        iv_note = self._iv_rationale(snapshot)

        if avg_signal > 0.05:
            direction = BiasDirection.BULLISH
            rationale = (
                f"Bullish momentum: price change {price_change_pct:.2%}, "
                f"RSI {snapshot.rsi_14:.1f}{iv_note}"
            )
        elif avg_signal < -0.05:
            direction = BiasDirection.BEARISH
            rationale = (
                f"Bearish momentum: price change {price_change_pct:.2%}, "
                f"RSI {snapshot.rsi_14:.1f}{iv_note}"
            )
        else:
            direction = BiasDirection.NEUTRAL
            adjusted_confidence = max(adjusted_confidence, 0.3)
            rationale = f"No clear direction: signal={avg_signal:.3f}{iv_note}"

        return MarketBias(
            direction=direction,
            confidence=ConfidenceScore(round(min(1.0, max(0.0, adjusted_confidence)), 4)),
            rationale=rationale,
        )

    @staticmethod
    def _iv_confidence_adjustment(snapshot: MarketSnapshot) -> float:
        """Return a confidence adjustment based on IV rank/percentile.

        High IV rank (>50%) is favourable for selling premium → positive boost.
        Low IV rank (<30%) is unfavourable → negative penalty.
        When IV data is absent, returns 0.
        """
        iv = snapshot.iv_rank if snapshot.iv_rank is not None else snapshot.iv_percentile
        if iv is None:
            return 0.0
        # Scale: iv=0.8 -> +0.06, iv=0.3 -> 0, iv=0.1 -> -0.04
        return (iv - 0.3) * 0.2

    @staticmethod
    def _iv_rationale(snapshot: MarketSnapshot) -> str:
        """Build an IV rationale fragment for the bias description."""
        parts: list[str] = []
        if snapshot.iv_rank is not None:
            parts.append(f"IVR {snapshot.iv_rank:.0%}")
        if snapshot.iv_percentile is not None:
            parts.append(f"IVP {snapshot.iv_percentile:.0%}")
        if parts:
            return ", " + ", ".join(parts)
        return ""


class DeltaBasedStrikeSelector:
    """Selects spread strikes based on delta targeting.

    Targets short strike near specified delta, places long strike
    at the configured spread width.
    """

    def __init__(self, target_short_delta: float = 0.20, spread_width: float = 5.0) -> None:
        self._target_delta = target_short_delta
        self._spread_width = spread_width

    def select_strikes(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Select strikes based on delta targeting for the given bias."""
        if bias.direction == BiasDirection.NEUTRAL:
            return NoTradeSignal(reason="Neutral bias: no trade recommended", bias=bias)

        if bias.direction == BiasDirection.BULLISH:
            return self._build_bull_put_spread(chain, bias, risk_params)
        else:
            return self._build_bear_call_spread(chain, bias, risk_params)

    def _build_bull_put_spread(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Build a bull put credit spread."""
        short_strike = self._find_put_strike_by_delta(chain, self._target_delta)
        if short_strike is None:
            return NoTradeSignal(reason="No suitable put strike found near target delta", bias=bias)

        long_strike_target = short_strike - self._spread_width
        if long_strike_target not in chain.put_premiums:
            nearest = self._nearest_strike(chain.strikes, long_strike_target, below=True)
            if nearest is None:
                return NoTradeSignal(reason="No long put strike available", bias=bias)
            long_strike_target = nearest
        long_strike = long_strike_target

        short_premium = chain.put_premiums.get(short_strike, 0.0)
        long_premium = chain.put_premiums.get(long_strike, 0.0)
        net_credit = short_premium - long_premium
        max_loss = abs(short_strike - long_strike) * 100 - net_credit * 100

        short_leg = SpreadLeg(
            strike=short_strike,
            expiry=chain.expiry,
            option_type="put",
            action="sell",
            premium=short_premium,
        )
        long_leg = SpreadLeg(
            strike=long_strike,
            expiry=chain.expiry,
            option_type="put",
            action="buy",
            premium=long_premium,
        )
        recommendation = SpreadRecommendation(
            spread_type=SpreadType.BULL_PUT,
            short_leg=short_leg,
            long_leg=long_leg,
            net_credit=net_credit * 100,
            max_loss=max_loss,
            bias=bias,
            rationale=f"Bull put spread: sell {short_strike}P / buy {long_strike}P",
        )

        if not passes_all_risk_checks(recommendation, bias, risk_params):
            return NoTradeSignal(
                reason="Recommendation failed risk checks",
                bias=bias,
            )
        return recommendation

    def _build_bear_call_spread(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Build a bear call credit spread."""
        short_strike = self._find_call_strike_by_delta(chain, self._target_delta)
        if short_strike is None:
            return NoTradeSignal(
                reason="No suitable call strike found near target delta", bias=bias
            )

        long_strike_target = short_strike + self._spread_width
        if long_strike_target not in chain.call_premiums:
            nearest = self._nearest_strike(chain.strikes, long_strike_target, below=False)
            if nearest is None:
                return NoTradeSignal(reason="No long call strike available", bias=bias)
            long_strike_target = nearest
        long_strike = long_strike_target

        short_premium = chain.call_premiums.get(short_strike, 0.0)
        long_premium = chain.call_premiums.get(long_strike, 0.0)
        net_credit = short_premium - long_premium
        max_loss = abs(long_strike - short_strike) * 100 - net_credit * 100

        short_leg = SpreadLeg(
            strike=short_strike,
            expiry=chain.expiry,
            option_type="call",
            action="sell",
            premium=short_premium,
        )
        long_leg = SpreadLeg(
            strike=long_strike,
            expiry=chain.expiry,
            option_type="call",
            action="buy",
            premium=long_premium,
        )
        recommendation = SpreadRecommendation(
            spread_type=SpreadType.BEAR_CALL,
            short_leg=short_leg,
            long_leg=long_leg,
            net_credit=net_credit * 100,
            max_loss=max_loss,
            bias=bias,
            rationale=f"Bear call spread: sell {short_strike}C / buy {long_strike}C",
        )

        if not passes_all_risk_checks(recommendation, bias, risk_params):
            return NoTradeSignal(
                reason="Recommendation failed risk checks",
                bias=bias,
            )
        return recommendation

    def _find_put_strike_by_delta(self, chain: OptionsChain, target_delta: float) -> float | None:
        """Find the put strike closest to the target absolute delta."""
        if not chain.put_deltas:
            return self._nearest_strike(chain.strikes, chain.underlying_price * 0.98, below=True)
        best_strike = None
        best_diff = float("inf")
        for strike, delta in chain.put_deltas.items():
            diff = abs(abs(delta) - target_delta)
            if diff < best_diff:
                best_diff = diff
                best_strike = strike
        return best_strike

    def _find_call_strike_by_delta(self, chain: OptionsChain, target_delta: float) -> float | None:
        """Find the call strike closest to the target absolute delta."""
        if not chain.call_deltas:
            return self._nearest_strike(chain.strikes, chain.underlying_price * 1.02, below=False)
        best_strike = None
        best_diff = float("inf")
        for strike, delta in chain.call_deltas.items():
            diff = abs(abs(delta) - target_delta)
            if diff < best_diff:
                best_diff = diff
                best_strike = strike
        return best_strike

    @staticmethod
    def _nearest_strike(strikes: list[float], target: float, below: bool) -> float | None:
        """Find the nearest available strike at or below/above a target."""
        candidates = [s for s in strikes if (s <= target if below else s >= target)]
        if not candidates:
            return None
        return max(candidates) if below else min(candidates)


class ProbabilityOfProfitStrikeSelector:
    """Selects spread strikes based on a target probability of profit.

    Converts the target PoP into an equivalent delta threshold
    (target_delta = 1 - target_pop) and delegates strike selection to
    DeltaBasedStrikeSelector. The rationale includes the estimated PoP so
    traders can reason in PoP terms rather than raw delta.
    """

    def __init__(self, target_pop: float, spread_width: float = 10.0) -> None:
        self._target_pop = target_pop
        self._inner = DeltaBasedStrikeSelector(
            target_short_delta=1.0 - target_pop,
            spread_width=spread_width,
        )

    def select_strikes(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Select strikes targeting the configured probability of profit."""
        result = self._inner.select_strikes(chain, bias, risk_params)
        if not isinstance(result, SpreadRecommendation):
            return result
        pop_pct = f"{self._target_pop:.0%}"
        return SpreadRecommendation(
            spread_type=result.spread_type,
            short_leg=result.short_leg,
            long_leg=result.long_leg,
            net_credit=result.net_credit,
            max_loss=result.max_loss,
            bias=result.bias,
            rationale=f"{result.rationale} (est. PoP: {pop_pct})",
        )


class RiskRewardStrikeSelector:
    """Selects spread strikes by targeting a desired risk-reward ratio.

    Iterates candidate spread widths from min_spread_width to max_spread_width
    in steps of step, evaluates each via DeltaBasedStrikeSelector, and picks
    the width whose resulting R/R ratio is closest to target_rr_ratio.
    This allows the spread width to vary dynamically rather than being fixed
    upfront, letting the market structure determine the optimal width for the
    desired payoff profile.
    """

    def __init__(
        self,
        target_short_delta: float = 0.20,
        target_rr_ratio: float = 5.0,
        min_spread_width: float = 5.0,
        max_spread_width: float = 25.0,
        step: float = 5.0,
    ) -> None:
        self._target_delta = target_short_delta
        self._target_rr = target_rr_ratio
        self._min_width = min_spread_width
        self._max_width = max_spread_width
        self._step = step

    def select_strikes(
        self,
        chain: OptionsChain,
        bias: MarketBias,
        risk_params: RiskParameters,
    ) -> SpreadRecommendation | NoTradeSignal:
        """Select strikes whose R/R ratio is closest to the configured target."""
        if bias.direction == BiasDirection.NEUTRAL:
            return NoTradeSignal(reason="Neutral bias: no trade recommended", bias=bias)

        best: SpreadRecommendation | None = None
        best_diff = float("inf")
        width = self._min_width
        while width <= self._max_width:
            selector = DeltaBasedStrikeSelector(
                target_short_delta=self._target_delta,
                spread_width=width,
            )
            candidate = selector.select_strikes(chain, bias, risk_params)
            if isinstance(candidate, SpreadRecommendation):
                diff = abs(candidate.risk_reward_ratio - self._target_rr)
                if diff < best_diff:
                    best_diff = diff
                    best = candidate
            width += self._step

        if best is None:
            return NoTradeSignal(reason="No spread found matching target R/R", bias=bias)

        return SpreadRecommendation(
            spread_type=best.spread_type,
            short_leg=best.short_leg,
            long_leg=best.long_leg,
            net_credit=best.net_credit,
            max_loss=best.max_loss,
            bias=best.bias,
            rationale=(
                f"{best.rationale} "
                f"(target R/R: {self._target_rr:.1f}, actual: {best.risk_reward_ratio:.1f})"
            ),
        )
