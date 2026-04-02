"""Tests for the FastAPI web adapter."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from strike_pilot.adapters.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    # Use context manager so the lifespan (and startup state) is properly initialised
    with TestClient(create_app()) as c:
        yield c  # type: ignore[misc]


class TestHealthEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.json() == {"status": "ok"}


class TestLivenessProbe:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health/live")
        assert response.json() == {"status": "ok"}


class TestReadinessProbe:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health/ready")
        assert response.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health/ready")
        assert response.json() == {"status": "ok"}


class TestStartupProbe:
    def test_returns_200(self, client: TestClient) -> None:
        response = client.get("/health/startup")
        assert response.status_code == 200

    def test_returns_status_ok(self, client: TestClient) -> None:
        response = client.get("/health/startup")
        assert response.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    def test_returns_200_with_defaults(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        assert response.status_code == 200

    def test_response_has_bias(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        data = response.json()
        assert "bias" in data

    def test_bias_has_required_fields(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        bias = response.json()["bias"]
        assert "direction" in bias
        assert "confidence" in bias
        assert "rationale" in bias

    def test_response_has_recommendation(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        data = response.json()
        assert "recommendation" in data

    def test_recommendation_has_action_field(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        rec = response.json()["recommendation"]
        assert "action" in rec
        assert rec["action"] in ("trade", "no_trade")

    def test_trade_recommendation_has_spread_fields(self, client: TestClient) -> None:
        # Permissive risk params guarantee a trade is recommended with static data
        response = client.post(
            "/analyze",
            json={
                "risk_params": {
                    "max_loss_dollars": 9999.0,
                    "min_credit_dollars": 1.0,
                    "max_spread_width": 100.0,
                    "min_confidence_threshold": 0.1,
                }
            },
        )
        rec = response.json()["recommendation"]
        assert rec["action"] == "trade"
        assert "spread_type" in rec
        assert "short_leg" in rec
        assert "long_leg" in rec
        assert "net_credit" in rec
        assert "max_loss" in rec
        assert "risk_reward_ratio" in rec

    def test_no_trade_recommendation_has_reason(self, client: TestClient) -> None:
        # Impossibly strict threshold forces no-trade
        response = client.post(
            "/analyze",
            json={
                "risk_params": {
                    "max_loss_dollars": 1000.0,
                    "min_credit_dollars": 50.0,
                    "max_spread_width": 10.0,
                    "min_confidence_threshold": 0.99,
                }
            },
        )
        rec = response.json()["recommendation"]
        assert rec["action"] == "no_trade"
        assert "reason" in rec

    def test_pop_strategy_returns_200(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"strategy": "pop", "target_pop": 0.75})
        assert response.status_code == 200

    def test_risk_reward_strategy_returns_200(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"strategy": "risk-reward", "target_rr": 4.0})
        assert response.status_code == 200

    def test_invalid_strategy_returns_422(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"strategy": "gamma"})
        assert response.status_code == 422

    def test_negative_max_loss_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            json={"risk_params": {"max_loss_dollars": -100.0}},
        )
        assert response.status_code == 422

    def test_zero_min_credit_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            json={"risk_params": {"min_credit_dollars": 0.0}},
        )
        assert response.status_code == 422

    def test_confidence_above_one_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/analyze",
            json={"risk_params": {"min_confidence_threshold": 1.5}},
        )
        assert response.status_code == 422

    def test_explicit_expiry_accepted(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"expiry": "2024-02-16"})
        assert response.status_code == 200
