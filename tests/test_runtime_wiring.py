import asyncio
from typing import Any

import httpx
from httpx import ASGITransport

from app.coordinator.service import CoordinatorDispatchResult
from app.main import app
from app.observability.provenance import NodeExecutionRecord
from app.schemas.contracts import ScenarioView, SpecialistResponse


def test_create_job_route_is_wired_in_default_app() -> None:
    original_dispatch = app.state.coordinator_service.dispatch
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
        app.state.coordinator_service.dispatch = original_dispatch  # type: ignore[method-assign]

    assert hasattr(app.state, "coordinator_service")
    assert response.status_code == 201
    assert response.json()["status"] == "completed"


def test_demo_submit_route_is_wired_in_default_app() -> None:
    original_dispatch = app.state.coordinator_service.dispatch
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
        app.state.coordinator_service.dispatch = original_dispatch  # type: ignore[method-assign]

    assert hasattr(app.state, "coordinator_service")
    assert response.status_code == 303
    assert response.headers["location"] == "/"


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
