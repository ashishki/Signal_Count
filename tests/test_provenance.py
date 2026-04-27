import asyncio
from pathlib import Path

import httpx
from httpx import ASGITransport

from app.coordinator.service import CoordinatorDispatchResult
from app.coordinator.synthesis import MemoSynthesisService
from app.main import app
from app.observability.provenance import NodeExecutionRecord
from app.schemas.contracts import ScenarioView, SpecialistResponse, ThesisRequest
from app.store import JobStore


class StubCoordinator:
    async def dispatch(
        self,
        job_id: str,
        request: ThesisRequest,
    ) -> CoordinatorDispatchResult:
        return CoordinatorDispatchResult(
            responses=[
                _specialist_response(
                    job_id=job_id,
                    node_role="regime",
                    peer_id="peer-regime-test",
                    summary="Liquidity regime stays constructive.",
                ),
                _specialist_response(
                    job_id=job_id,
                    node_role="narrative",
                    peer_id="peer-narrative-test",
                    summary="ETF flow narrative remains supportive.",
                ),
                _specialist_response(
                    job_id=job_id,
                    node_role="risk",
                    peer_id="peer-risk-test",
                    summary="Loss of support invalidates the thesis.",
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
            market_snapshot={"price_return": 0.08},
            news_headlines=["ETF flows remain constructive"],
            node_execution_records=[
                NodeExecutionRecord(
                    node_role="regime",
                    peer_id="peer-regime-test",
                    service_name="regime_analyst",
                    transport="axl-mcp",
                    dispatch_target="/mcp/peer-regime-test/regime_analyst",
                    status="completed",
                    latency_ms=12.5,
                ),
                NodeExecutionRecord(
                    node_role="narrative",
                    peer_id="peer-narrative-test",
                    service_name="narrative_analyst",
                    transport="axl-mcp",
                    dispatch_target="/mcp/peer-narrative-test/narrative_analyst",
                    status="completed",
                    latency_ms=19.0,
                ),
                NodeExecutionRecord(
                    node_role="risk",
                    peer_id="peer-risk-test",
                    service_name="risk_analyst",
                    transport="axl-mcp",
                    dispatch_target="/mcp/peer-risk-test/risk_analyst",
                    status="completed",
                    latency_ms=17.25,
                ),
            ],
            run_metadata={
                "run_mode": "live-axl",
                "expected_roles": ["regime", "narrative", "risk"],
                "completed_roles": ["regime", "narrative", "risk"],
                "missing_roles": [],
                "dispatch_targets": [
                    "/mcp/peer-regime-test/regime_analyst",
                    "/mcp/peer-narrative-test/narrative_analyst",
                    "/mcp/peer-risk-test/risk_analyst",
                ],
            },
        )


class FailingLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        raise RuntimeError("force fallback path")


def test_job_record_contains_per_node_status_and_latency(tmp_path: Path) -> None:
    payload = asyncio.run(_run_job_flow(tmp_path))

    assert payload["provenance_ledger"] == [
        {
            "node_role": "regime",
            "peer_id": "peer-regime-test",
            "status": "completed",
            "latency_ms": 12.5,
            "service_name": "regime_analyst",
            "transport": "axl-mcp",
            "dispatch_target": "/mcp/peer-regime-test/regime_analyst",
        },
        {
            "node_role": "narrative",
            "peer_id": "peer-narrative-test",
            "status": "completed",
            "latency_ms": 19.0,
            "service_name": "narrative_analyst",
            "transport": "axl-mcp",
            "dispatch_target": "/mcp/peer-narrative-test/narrative_analyst",
        },
        {
            "node_role": "risk",
            "peer_id": "peer-risk-test",
            "status": "completed",
            "latency_ms": 17.25,
            "service_name": "risk_analyst",
            "transport": "axl-mcp",
            "dispatch_target": "/mcp/peer-risk-test/risk_analyst",
        },
    ]


def test_job_record_contains_topology_snapshot(tmp_path: Path) -> None:
    payload = asyncio.run(_run_job_flow(tmp_path))

    assert payload["topology_snapshot"] == {
        "local_peer_id": "peer-coordinator-test",
        "peers": [
            "peer-regime-test",
            "peer-narrative-test",
            "peer-risk-test",
        ],
    }


def test_job_record_contains_run_metadata(tmp_path: Path) -> None:
    payload = asyncio.run(_run_job_flow(tmp_path))

    assert payload["run_metadata"] == {
        "run_mode": "live-axl",
        "expected_roles": ["regime", "narrative", "risk"],
        "completed_roles": ["regime", "narrative", "risk"],
        "missing_roles": [],
        "dispatch_targets": [
            "/mcp/peer-regime-test/regime_analyst",
            "/mcp/peer-narrative-test/narrative_analyst",
            "/mcp/peer-risk-test/risk_analyst",
        ],
    }


async def _run_job_flow(tmp_path: Path) -> dict[str, object]:
    database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    app.state.job_store = JobStore(database_url=database_url)
    app.state.coordinator_service = StubCoordinator()
    app.state.memo_synthesis_service = MemoSynthesisService(
        llm_client=FailingLLMClient()
    )
    await app.state.job_store.initialize()

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        create_response = await client.post(
            "/jobs",
            json={
                "thesis": "ETH can rally on improving ETF flows.",
                "asset": "ETH",
                "horizon_days": 30,
            },
        )
        job_id = create_response.json()["job_id"]
        get_response = await client.get(f"/jobs/{job_id}")

    return get_response.json()


def _specialist_response(
    job_id: str,
    node_role: str,
    peer_id: str,
    summary: str,
) -> SpecialistResponse:
    return SpecialistResponse(
        job_id=job_id,
        node_role=node_role,
        peer_id=peer_id,
        summary=summary,
        scenario_view=ScenarioView(bull=0.4, base=0.4, bear=0.2),
        signals=[],
        risks=[],
        confidence=0.7,
        citations=[],
        timestamp="2026-04-24T00:00:00Z",
    )
