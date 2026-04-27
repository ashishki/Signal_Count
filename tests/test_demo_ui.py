import asyncio
from pathlib import Path

import httpx
from httpx import ASGITransport

from app.coordinator.service import CoordinatorDispatchResult
from app.coordinator.synthesis import MemoSynthesisService
from app.demo.fixtures import get_demo_fixture
from app.main import app
from app.schemas.contracts import (
    FinalMemo,
    ProvenanceRecord,
    ScenarioView,
    ThesisRequest,
)
from app.store import JobStore


class FailingLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        raise RuntimeError("force fallback path")


class StubCoordinator:
    async def dispatch(
        self,
        job_id: str,
        request: ThesisRequest,
    ) -> CoordinatorDispatchResult:
        return CoordinatorDispatchResult(
            responses=[],
            topology_snapshot={
                "local_peer_id": "peer-coordinator-test",
                "peers": [],
            },
            market_snapshot={},
            news_headlines=[],
        )


def test_home_page_renders_form_and_latest_job_summary(tmp_path: Path) -> None:
    asyncio.run(_configure_completed_job(tmp_path))

    async def _exercise() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get("/")

    response = asyncio.run(_exercise())

    assert response.status_code == 200
    html = response.text
    assert '<form action="/demo/submit" method="post">' in html
    assert '<form action="/demo/replay/eth-etf-flow" method="post">' in html
    assert "Latest Job" in html
    assert "Run Evidence" in html
    assert "Run Metadata" in html
    assert "Job ID:" in html
    assert "Will ETH validate this thesis over 30 days" in html
    assert "peer-regime-test" in html
    assert "Topology Snapshot" in html


def test_demo_submit_redirects_back_to_home_with_new_job(tmp_path: Path) -> None:
    asyncio.run(_configure_empty_store(tmp_path))

    async def _exercise() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            submit_response = await client.post(
                "/demo/submit",
                data={
                    "thesis": "ETH can rally on improving ETF flows.",
                    "asset": "ETH",
                    "horizon_days": "30",
                },
            )
            home_response = await client.get("/")
            return submit_response, home_response

    submit_response, home_response = asyncio.run(_exercise())

    assert submit_response.status_code == 303
    assert submit_response.headers["location"] == "/"
    assert "Latest Job" in home_response.text
    assert "ETH can rally on improving ETF flows." in home_response.text


def test_demo_submit_returns_422_for_invalid_horizon(tmp_path: Path) -> None:
    asyncio.run(_configure_empty_store(tmp_path))

    async def _exercise() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            return await client.post(
                "/demo/submit",
                data={
                    "thesis": "ETH can rally on improving ETF flows.",
                    "asset": "ETH",
                    "horizon_days": "abc",
                },
            )

    response = asyncio.run(_exercise())

    assert response.status_code == 422
    assert "horizon_days" in response.text


def test_demo_replay_fixture_redirects_back_to_home_with_fixture_job(
    tmp_path: Path,
) -> None:
    asyncio.run(_configure_empty_store(tmp_path))

    async def _exercise() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            follow_redirects=False,
        ) as client:
            replay_response = await client.post("/demo/replay/eth-etf-flow")
            home_response = await client.get("/")
            return replay_response, home_response

    replay_response, home_response = asyncio.run(_exercise())

    assert replay_response.status_code == 303
    assert replay_response.headers["location"] == "/"
    assert "ETH ETF Flow Case" in home_response.text
    assert (
        "ETH can rally on improving ETF flows and stable liquidity."
        in home_response.text
    )


def test_demo_fixture_loader_returns_replayable_thesis_case() -> None:
    fixture = get_demo_fixture("eth-etf-flow")

    assert fixture.fixture_id == "eth-etf-flow"
    assert fixture.asset == "ETH"
    assert fixture.horizon_days == 30
    assert "ETF flows" in fixture.thesis
    assert fixture.to_dict()["title"] == "ETH ETF Flow Case"


def test_home_page_handles_live_axl_topology_shape(tmp_path: Path) -> None:
    asyncio.run(_configure_completed_job_with_axl_topology(tmp_path))

    async def _exercise() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get("/")

    response = asyncio.run(_exercise())

    assert response.status_code == 200
    assert "Topology Snapshot" in response.text
    assert "axl-public-key-test" in response.text


async def _configure_completed_job(tmp_path: Path) -> None:
    app.state.job_store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    app.state.memo_synthesis_service = MemoSynthesisService(
        llm_client=FailingLLMClient()
    )
    await app.state.job_store.initialize()
    job = await app.state.job_store.create_job(
        ThesisRequest(
            thesis="ETH can rally on improving ETF flows.",
            asset="ETH",
            horizon_days=30,
        )
    )
    await app.state.job_store.complete_job(
        job_id=job.job_id,
        memo=FinalMemo(
            job_id=job.job_id,
            normalized_thesis=(
                "Will ETH validate this thesis over 30 days: "
                "ETH can rally on improving ETF flows."
            ),
            scenarios=ScenarioView(bull=0.42, base=0.36, bear=0.22),
            catalysts=["ETF flows remain constructive."],
            risks=["Macro volatility can pressure beta assets."],
            invalidation_triggers=["ETH loses the recent support range."],
            provenance=[
                ProvenanceRecord(
                    node_role="regime",
                    peer_id="peer-regime-test",
                    timestamp="2026-04-24T00:00:00Z",
                )
            ],
            partial=False,
            partial_reason=None,
        ),
        provenance_ledger=[
            {
                "node_role": "regime",
                "peer_id": "peer-regime-test",
                "service_name": "regime_analyst",
                "transport": "axl-mcp",
                "dispatch_target": "/mcp/peer-regime-test/regime_analyst",
                "status": "completed",
                "latency_ms": 12.5,
            }
        ],
        run_metadata={
            "run_mode": "live-axl",
            "transport": "axl-mcp",
            "axl_local_base_url": "http://127.0.0.1:9002",
            "dispatch_targets": ["/mcp/peer-regime-test/regime_analyst"],
        },
        topology_snapshot={
            "local_peer_id": "peer-coordinator-test",
            "peers": ["peer-regime-test"],
        },
    )


async def _configure_empty_store(tmp_path: Path) -> None:
    app.state.job_store = JobStore(database_url=f"sqlite:///{tmp_path / 'jobs.db'}")
    app.state.coordinator_service = StubCoordinator()
    app.state.memo_synthesis_service = MemoSynthesisService(
        llm_client=FailingLLMClient()
    )
    await app.state.job_store.initialize()


async def _configure_completed_job_with_axl_topology(tmp_path: Path) -> None:
    await _configure_completed_job(tmp_path)
    latest_job = await app.state.job_store.get_latest_job()
    assert latest_job is not None
    await app.state.job_store.complete_job(
        job_id=latest_job.job_id,
        memo=FinalMemo.model_validate(latest_job.memo),
        provenance_ledger=latest_job.provenance_ledger,
        run_metadata=latest_job.run_metadata,
        topology_snapshot={
            "our_public_key": "axl-public-key-test",
            "peers": None,
            "tree": [
                {
                    "public_key": "axl-public-key-test",
                    "parent": "axl-public-key-test",
                    "sequence": 1,
                }
            ],
        },
    )
