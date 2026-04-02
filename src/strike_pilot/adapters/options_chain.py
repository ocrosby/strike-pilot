"""Options chain adapter implementations.

Provides mock/static options chain data for development and testing.
"""

from __future__ import annotations

from strike_pilot.domain.models import OptionsChain


class StaticOptionsChainAdapter:
    """Adapter returning static/mock options chain data for SPX.

    Useful for development, demos, and testing. Generates plausible
    put and call premiums around the given underlying price.
    """

    def get_chain(self, symbol: str, expiry: str) -> OptionsChain:
        """Return a mock options chain centered on a typical SPX price."""
        underlying = 5250.0
        # Wide range: ~10% OTM on each side ensures realistic delta coverage
        strikes = [float(s) for s in range(4700, 5800, 5)]

        call_premiums: dict[float, float] = {}
        put_premiums: dict[float, float] = {}
        call_deltas: dict[float, float] = {}
        put_deltas: dict[float, float] = {}

        for strike in strikes:
            dist = (strike - underlying) / underlying
            # Simplified premium and delta generation (not Black-Scholes)
            if dist >= 0:
                # OTM call
                call_prem = max(0.5, 20.0 * (1.0 - dist * 25))
                call_delta = max(0.05, 0.5 - dist * 10)
            else:
                # ITM call
                call_prem = max(0.5, 20.0 + abs(dist) * 1000)
                call_delta = min(0.95, 0.5 + abs(dist) * 10)

            if dist <= 0:
                # OTM put
                put_prem = max(0.5, 20.0 * (1.0 - abs(dist) * 25))
                put_delta = max(0.05, 0.5 - abs(dist) * 10)
            else:
                # ITM put
                put_prem = max(0.5, 20.0 + dist * 1000)
                put_delta = min(0.95, 0.5 + dist * 10)

            call_premiums[strike] = round(call_prem, 2)
            put_premiums[strike] = round(put_prem, 2)
            call_deltas[strike] = round(call_delta, 4)
            put_deltas[strike] = round(-put_delta, 4)  # puts have negative delta

        return OptionsChain(
            symbol=symbol,
            expiry=expiry,
            underlying_price=underlying,
            strikes=strikes,
            call_premiums=call_premiums,
            put_premiums=put_premiums,
            call_deltas=call_deltas,
            put_deltas=put_deltas,
        )
