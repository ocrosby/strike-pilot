"""Synthetic options chain adapter using Black-Scholes pricing.

When real historical options chain data is unavailable (which is typical for
free data sources), this adapter reconstructs approximate option prices and
deltas analytically from:

  - Underlying price from a MarketSnapshot
  - Implied volatility proxied by VIX / 100
  - Time to expiry derived from the snapshot timestamp and expiry date
  - A configurable risk-free rate

This enables meaningful backtesting without paid data, at the cost of
simplified pricing (constant vol, no skew, no term structure).
"""

from __future__ import annotations

from datetime import date
from math import exp, log, sqrt
from statistics import NormalDist

from strike_pilot.domain.models import MarketSnapshot, OptionsChain

_NORM = NormalDist()


def _black_scholes(
    spot: float, strike: float, tte: float, r: float, sigma: float
) -> tuple[float, float, float, float]:
    """Compute Black-Scholes call/put prices and deltas.

    Args:
        spot: Underlying price.
        strike: Strike price.
        tte: Time to expiry in years (0 = at expiry).
        r: Continuously compounded risk-free rate.
        sigma: Annualised implied volatility (e.g. 0.165 for 16.5%).

    Returns:
        Tuple of (call_price, put_price, call_delta, put_delta).
    """
    if tte <= 0.0 or sigma <= 0.0:
        call_price = max(0.0, spot - strike)
        put_price = max(0.0, strike - spot)
        call_delta = 1.0 if spot > strike else (0.5 if spot == strike else 0.0)
        put_delta = -1.0 if spot < strike else (-0.5 if spot == strike else 0.0)
        return call_price, put_price, call_delta, put_delta

    d1 = (log(spot / strike) + (r + sigma**2 / 2.0) * tte) / (sigma * sqrt(tte))
    d2 = d1 - sigma * sqrt(tte)

    call_price = spot * _NORM.cdf(d1) - strike * exp(-r * tte) * _NORM.cdf(d2)
    put_price = strike * exp(-r * tte) * _NORM.cdf(-d2) - spot * _NORM.cdf(-d1)
    call_delta = _NORM.cdf(d1)
    put_delta = _NORM.cdf(d1) - 1.0  # equivalent to -N(-d1)

    return max(0.0, call_price), max(0.0, put_price), call_delta, put_delta


class SyntheticOptionsChainAdapter:
    """Generates a synthetic options chain from a market snapshot.

    Prices options using Black-Scholes with VIX as the IV proxy. Strikes
    are generated at uniform intervals centred on the current underlying
    price, rounded to the nearest strike_step.
    """

    def __init__(
        self,
        snapshot: MarketSnapshot,
        strike_step: float = 5.0,
        num_strikes: int = 40,
        risk_free_rate: float = 0.05,
    ) -> None:
        self._snapshot = snapshot
        self._step = strike_step
        self._num_strikes = num_strikes
        self._r = risk_free_rate

    def get_chain(self, symbol: str, expiry: str) -> OptionsChain:
        """Generate a synthetic options chain for the given expiry.

        Args:
            symbol: Market symbol (stored in the returned chain for reference).
            expiry: ISO date string for the options expiry.

        Returns:
            An OptionsChain with Black-Scholes prices and deltas for all strikes.
        """
        price = self._snapshot.price
        sigma = max(0.05, self._snapshot.vix / 100.0)

        snap_date = date.fromisoformat(self._snapshot.timestamp[:10])
        expiry_date = date.fromisoformat(expiry)
        tte = max(0.0, (expiry_date - snap_date).days / 365.25)

        atm = round(price / self._step) * self._step
        half = self._num_strikes // 2
        strikes = [atm + (i - half) * self._step for i in range(self._num_strikes)]

        call_premiums: dict[float, float] = {}
        put_premiums: dict[float, float] = {}
        call_deltas: dict[float, float] = {}
        put_deltas: dict[float, float] = {}

        for k in strikes:
            call_p, put_p, call_d, put_d = _black_scholes(price, k, tte, self._r, sigma)
            call_premiums[k] = round(call_p, 2)
            put_premiums[k] = round(put_p, 2)
            call_deltas[k] = round(call_d, 4)
            put_deltas[k] = round(put_d, 4)

        return OptionsChain(
            symbol=symbol,
            expiry=expiry,
            underlying_price=price,
            strikes=strikes,
            call_premiums=call_premiums,
            put_premiums=put_premiums,
            call_deltas=call_deltas,
            put_deltas=put_deltas,
        )
