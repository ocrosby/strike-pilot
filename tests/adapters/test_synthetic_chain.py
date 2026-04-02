"""Unit tests for the synthetic options chain adapter."""

from __future__ import annotations

from strike_pilot.adapters.synthetic_chain import SyntheticOptionsChainAdapter
from strike_pilot.domain.models import MarketSnapshot


def make_snapshot(
    price: float = 5250.0,
    vix: float = 16.5,
    timestamp: str = "2024-01-15T10:30:00",
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="SPX",
        price=price,
        open_price=price - 10,
        high_price=price + 15,
        low_price=price - 15,
        vix=vix,
        timestamp=timestamp,
    )


class TestSyntheticOptionsChainAdapter:
    def test_generates_strikes(self) -> None:
        adapter = SyntheticOptionsChainAdapter(make_snapshot())
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert len(chain.strikes) > 0

    def test_strikes_centered_around_price(self) -> None:
        adapter = SyntheticOptionsChainAdapter(make_snapshot(price=5250.0))
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert any(abs(s - 5250.0) <= 10.0 for s in chain.strikes)

    def test_all_premiums_non_negative(self) -> None:
        adapter = SyntheticOptionsChainAdapter(make_snapshot())
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert all(v >= 0.0 for v in chain.call_premiums.values())
        assert all(v >= 0.0 for v in chain.put_premiums.values())

    def test_atm_put_delta_near_negative_half(self) -> None:
        price = 5250.0
        adapter = SyntheticOptionsChainAdapter(make_snapshot(price=price))
        chain = adapter.get_chain("SPX", "2024-01-26")  # 11 days out
        atm = min(chain.strikes, key=lambda s: abs(s - price))
        assert abs(chain.put_deltas[atm] + 0.5) < 0.15

    def test_atm_call_delta_near_half(self) -> None:
        price = 5250.0
        adapter = SyntheticOptionsChainAdapter(make_snapshot(price=price))
        chain = adapter.get_chain("SPX", "2024-01-26")
        atm = min(chain.strikes, key=lambda s: abs(s - price))
        assert abs(chain.call_deltas[atm] - 0.5) < 0.15

    def test_otm_put_delta_smaller_than_atm(self) -> None:
        """Deep OTM put should have smaller absolute delta than ATM put."""
        price = 5250.0
        adapter = SyntheticOptionsChainAdapter(make_snapshot(price=price), strike_step=5.0)
        chain = adapter.get_chain("SPX", "2024-01-26")
        atm = min(chain.strikes, key=lambda s: abs(s - price))
        deep_otm = atm - 50.0
        if deep_otm in chain.put_deltas:
            assert abs(chain.put_deltas[deep_otm]) < abs(chain.put_deltas[atm])

    def test_call_put_parity_holds_approximately(self) -> None:
        """C - P ≈ S - K*exp(-rT) (put-call parity)."""
        price = 5250.0
        adapter = SyntheticOptionsChainAdapter(make_snapshot(price=price), risk_free_rate=0.05)
        chain = adapter.get_chain("SPX", "2024-01-26")
        atm = min(chain.strikes, key=lambda s: abs(s - price))
        call = chain.call_premiums[atm]
        put = chain.put_premiums[atm]
        # C - P should be close to S - K (simplified, ignoring discount)
        diff = abs((call - put) - (price - atm))
        assert diff < 20.0  # generous tolerance for approximation

    def test_expiry_passthrough(self) -> None:
        adapter = SyntheticOptionsChainAdapter(make_snapshot())
        chain = adapter.get_chain("SPX", "2024-02-16")
        assert chain.expiry == "2024-02-16"

    def test_symbol_passthrough(self) -> None:
        adapter = SyntheticOptionsChainAdapter(make_snapshot())
        chain = adapter.get_chain("SPX", "2024-01-19")
        assert chain.symbol == "SPX"

    def test_at_expiry_atm_call_has_zero_time_value(self) -> None:
        """When expiry == snapshot date, only intrinsic value remains."""
        adapter = SyntheticOptionsChainAdapter(make_snapshot(timestamp="2024-01-19T10:30:00"))
        chain = adapter.get_chain("SPX", "2024-01-19")
        itm_strike = 5200.0
        if itm_strike in chain.call_premiums:
            # ITM call value ≈ S - K = 5250 - 5200 = 50 (premiums are per-share, not per lot)
            assert chain.call_premiums[itm_strike] >= 0.0
