import asyncio
from pathlib import Path
from typing import Any

import httpx
from httpx import ASGITransport

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.coordinator.service import CoordinatorDispatchResult, CoordinatorService
from app.main import app
from app.nodes.verifier.service import VerifierService
from app.observability.provenance import NodeExecutionRecord
from app.schemas.contracts import ScenarioView, SpecialistResponse, ThesisRequest
from app.store import JobStore


def test_create_job_route_is_wired_in_default_app(tmp_path: Path) -> None:
    original_store = app.state.job_store
    original_dispatch = app.state.coordinator_service.dispatch
    app.state.job_store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    app.state.coordinator_service.dispatch = _stub_dispatch  # type: ignore[method-assign]

    try:
        response = asyncio.run(
            _post_json(
                "/jobs",
                {
                    "thesis": "ETH can rally on improving ETF flows.",
                    "asset": "ETH",
                    "horizon_days": 30,
                },
            )
        )
    finally:
        app.state.job_store = original_store
        app.state.coordinator_service.dispatch = original_dispatch  # type: ignore[method-assign]

    assert hasattr(app.state, "coordinator_service")
    assert response.status_code == 201
    assert response.json()["status"] == "completed"


def test_demo_submit_route_is_wired_in_default_app(tmp_path: Path) -> None:
    original_store = app.state.job_store
    original_dispatch = app.state.coordinator_service.dispatch
    app.state.job_store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    app.state.coordinator_service.dispatch = _stub_dispatch  # type: ignore[method-assign]

    try:
        response = asyncio.run(
            _post_form(
                "/demo/submit",
                {
                    "thesis": "ETH can rally on improving ETF flows.",
                    "asset": "ETH",
                    "horizon_days": "30",
                },
            )
        )
    finally:
        app.state.job_store = original_store
        app.state.coordinator_service.dispatch = original_dispatch  # type: ignore[method-assign]

    assert hasattr(app.state, "coordinator_service")
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_ree_policy_is_recorded_in_run_metadata() -> None:
    service = CoordinatorService(
        axl_client=_PolicyAXLClient(),
        registry=AXLRegistry(Settings()),
        market_data_provider=_PolicyMarketDataProvider(),
        news_feed_provider=_PolicyNewsFeedProvider(),
        llm_client=object(),
        verifier=VerifierService(
            ree_policy="risk-only-ree",
            enforce_ree_policy=True,
        ),
    )

    result = asyncio.run(
        service.dispatch(
            job_id="job-ree-policy",
            request=ThesisRequest(
                thesis="ETH can rally on improving ETF flows.",
                asset="ETH",
                horizon_days=30,
            ),
        )
    )

    assert result.run_metadata["ree_policy"] == "risk-only-ree"
    assert result.run_metadata["ree_policy_enforced"] is True


async def _post_json(path: str, payload: dict[str, object]) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        return await client.post(path, json=payload)


async def _post_form(path: str, payload: dict[str, str]) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        return await client.post(path, data=payload)


class _PolicyAXLClient:
    async def fetch_topology(self) -> dict[str, object]:
        return {"mode": "live-axl", "local_peer_id": "peer-coordinator-test"}

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, object],
    ) -> SpecialistResponse:
        return _response(
            job_id=str(payload["job_id"]),
            role=str(payload["role"]),
            peer_id=peer_id,
            summary=f"{service_name} completed.",
            signals=["policy test signal"],
            risks=["policy test risk"] if payload["role"] == "risk" else [],
        )


class _PolicyMarketDataProvider:
    async def fetch_snapshot(self, request: ThesisRequest) -> dict[str, float]:
        return {"price_return": 0.05, "volatility": 0.2}


class _PolicyNewsFeedProvider:
    async def fetch_headlines(self, request: ThesisRequest) -> list[str]:
        return ["Policy test headline"]


async def _stub_dispatch(*args: Any, **kwargs: Any) -> CoordinatorDispatchResult:
    request = kwargs["request"]
    job_id = kwargs["job_id"]
    return CoordinatorDispatchResult(
        responses=[
            _response(
                job_id=job_id,
                role="regime",
                peer_id="peer-regime-test",
                summary="Regime remains constructive.",
                signals=["Positive liquidity regime"],
                risks=[],
            ),
            _response(
                job_id=job_id,
                role="narrative",
                peer_id="peer-narrative-test",
                summary="Narrative remains constructive.",
                signals=[f"{request.asset} flows remain constructive"],
                risks=[],
            ),
            _response(
                job_id=job_id,
                role="risk",
                peer_id="peer-risk-test",
                summary="Loss of support invalidates the thesis.",
                signals=["invalidation: support break"],
                risks=["Macro volatility can pressure beta assets"],
            ),
        ],
        topology_snapshot={
            "local_peer_id": "peer-coordinator-test",
            "peers": [
                "peer-regime-test",
                "peer-narrative-test",
                "peer-risk-test",
            ],
        },
        market_snapshot={"price_return": 0.08, "volatility": 0.18},
        news_headlines=["ETF flows remain constructive"],
        node_execution_records=[
            NodeExecutionRecord(
                node_role="regime",
                peer_id="peer-regime-test",
                status="completed",
                latency_ms=12.0,
            ),
            NodeExecutionRecord(
                node_role="narrative",
                peer_id="peer-narrative-test",
                status="completed",
                latency_ms=16.0,
            ),
            NodeExecutionRecord(
                node_role="risk",
                peer_id="peer-risk-test",
                status="completed",
                latency_ms=18.0,
            ),
        ],
    )


def _response(
    *,
    job_id: str,
    role: str,
    peer_id: str,
    summary: str,
    signals: list[str],
    risks: list[str],
) -> SpecialistResponse:
    return SpecialistResponse(
        job_id=job_id,
        node_role=role,
        peer_id=peer_id,
        summary=summary,
        scenario_view=ScenarioView(bull=0.4, base=0.4, bear=0.2),
        signals=signals,
        risks=risks,
        confidence=0.7,
        citations=[],
        timestamp="2026-04-24T00:00:00Z",
    )
