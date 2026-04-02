"""FastAPI application factory for the Strike Pilot HTTP API.

This module is the inbound HTTP adapter. It wires the same use case that
the CLI uses, exposing it over HTTP without touching any domain logic.

Usage (programmatic):
    from strike_pilot.adapters.api.app import create_app
    app = create_app()

Usage (uvicorn):
    uvicorn strike_pilot.adapters.api.app:app
"""

from __future__ import annotations

from fastapi import FastAPI

from strike_pilot.adapters.api.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    BiasResponse,
    NoTradeResponse,
    SpreadLegResponse,
    SpreadRecommendationResponse,
)
from strike_pilot.adapters.clock import SystemClock
from strike_pilot.adapters.market_data import StaticMarketDataAdapter
from strike_pilot.adapters.options_chain import StaticOptionsChainAdapter
from strike_pilot.adapters.presenters import JsonPresenter
from strike_pilot.adapters.yfinance_market_data import YFinanceMarketDataAdapter
from strike_pilot.application.use_cases import AnalyzeAndRecommendUseCase
from strike_pilot.domain.models import (
    NoTradeSignal,
    RiskParameters,
    SpreadRecommendation,
)
from strike_pilot.domain.services import (
    DeltaBasedStrikeSelector,
    ProbabilityOfProfitStrikeSelector,
    RiskRewardStrikeSelector,
    SimpleMomentumBiasStrategy,
    StrikeSelectionStrategy,
)


def _build_use_case(req: AnalyzeRequest) -> AnalyzeAndRecommendUseCase:
    """Construct the use case from the request parameters."""
    risk_params = RiskParameters(
        max_loss_dollars=req.risk_params.max_loss_dollars,
        min_credit_dollars=req.risk_params.min_credit_dollars,
        max_spread_width=req.risk_params.max_spread_width,
        min_confidence_threshold=req.risk_params.min_confidence_threshold,
    )
    _ = risk_params  # validated; passed into execute below

    strike_selector: StrikeSelectionStrategy
    if req.strategy == "pop":
        strike_selector = ProbabilityOfProfitStrikeSelector(
            target_pop=req.target_pop,
            spread_width=req.spread_width,
        )
    elif req.strategy == "risk-reward":
        strike_selector = RiskRewardStrikeSelector(
            target_rr_ratio=req.target_rr,
            max_spread_width=req.spread_width,
        )
    else:
        strike_selector = DeltaBasedStrikeSelector(
            target_short_delta=0.20,
            spread_width=req.spread_width,
        )

    market_data = (
        YFinanceMarketDataAdapter() if req.data_source == "live" else StaticMarketDataAdapter()
    )

    return AnalyzeAndRecommendUseCase(
        market_data_provider=market_data,
        options_chain_provider=StaticOptionsChainAdapter(),
        bias_strategy=SimpleMomentumBiasStrategy(),
        strike_selector=strike_selector,
        presenter=JsonPresenter(),
        clock=SystemClock(),
    )


def _to_response(
    req: AnalyzeRequest,
    use_case: AnalyzeAndRecommendUseCase,
) -> AnalyzeResponse:
    """Execute the use case and map domain models to response models."""
    risk_params = RiskParameters(
        max_loss_dollars=req.risk_params.max_loss_dollars,
        min_credit_dollars=req.risk_params.min_credit_dollars,
        max_spread_width=req.risk_params.max_spread_width,
        min_confidence_threshold=req.risk_params.min_confidence_threshold,
    )
    bias, result = use_case.execute(
        symbol=req.symbol,
        risk_params=risk_params,
        expiry=req.expiry,
    )

    bias_resp = BiasResponse(
        direction=bias.direction.value,
        confidence=bias.confidence.value,
        rationale=bias.rationale,
    )

    if isinstance(result, SpreadRecommendation):
        rec_resp: SpreadRecommendationResponse | NoTradeResponse = SpreadRecommendationResponse(
            action="trade",
            spread_type=result.spread_type.value,
            short_leg=SpreadLegResponse(
                strike=result.short_leg.strike,
                expiry=result.short_leg.expiry,
                option_type=result.short_leg.option_type,
                action=result.short_leg.action,
                premium=result.short_leg.premium,
            ),
            long_leg=SpreadLegResponse(
                strike=result.long_leg.strike,
                expiry=result.long_leg.expiry,
                option_type=result.long_leg.option_type,
                action=result.long_leg.action,
                premium=result.long_leg.premium,
            ),
            net_credit=result.net_credit,
            max_loss=result.max_loss,
            risk_reward_ratio=round(result.risk_reward_ratio, 4),
            rationale=result.rationale,
        )
    else:
        assert isinstance(result, NoTradeSignal)
        rec_resp = NoTradeResponse(action="no_trade", reason=result.reason)

    return AnalyzeResponse(bias=bias_resp, recommendation=rec_resp)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Strike Pilot API",
        description="SPX intraday bias and credit spread recommendation engine",
        version="0.1.0",
    )

    @app.get("/health", summary="Health check (alias for /health/live)")
    def health() -> dict[str, str]:
        """Backward-compatible health check — delegates to the liveness probe."""
        return {"status": "ok"}

    @app.get("/health/live", summary="Liveness probe")
    def live() -> dict[str, str]:
        """Return 200 if the process is alive and the event loop is responsive.

        Kubernetes restarts the pod if this probe fails. Keep it cheap — no
        external dependency checks. If this endpoint can respond, the process
        is alive.
        """
        return {"status": "ok"}

    @app.get("/health/ready", summary="Readiness probe")
    def ready() -> dict[str, str]:
        """Return 200 if the service is ready to accept traffic.

        Kubernetes removes the pod from the load balancer (without restarting)
        if this probe fails. Extend this to check external dependencies — for
        example, verifying that a live market data feed is reachable — before
        returning 200.
        """
        return {"status": "ok"}

    @app.get("/health/startup", summary="Startup probe")
    def startup() -> dict[str, str]:
        """Return 200 once the application has finished initializing.

        Kubernetes uses this probe to give slow-starting containers extra time
        before the liveness probe begins. For a stateless app with no heavy
        initialization this passes immediately. Wire real startup work through
        the FastAPI lifespan context to gate this on completion.
        """
        return {"status": "ok"}

    @app.post("/analyze", response_model=AnalyzeResponse, summary="Analyze and recommend")
    def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
        """Run bias analysis and return a credit spread recommendation."""
        use_case = _build_use_case(req)
        return _to_response(req, use_case)

    return app


# Module-level instance for uvicorn direct invocation:
#   uvicorn strike_pilot.adapters.api.app:app
app = create_app()
