import asyncio
from pathlib import Path
from uuid import UUID

import httpx
from httpx import ASGITransport

from app.chain.receipts import ChainReceipt, JobChainReceipts
from app.coordinator.service import CoordinatorDispatchResult
from app.coordinator.synthesis import MemoSynthesisService
from app.evaluation.reputation import build_reputation_updates
from app.main import app
from app.schemas.contracts import (
    ScenarioView,
    SpecialistResponse,
    ThesisRequest,
    VerificationAttestation,
)
from app.store import JobStore


class StubCoordinator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ThesisRequest]] = []

    async def dispatch(
        self,
        job_id: str,
        request: ThesisRequest,
    ) -> CoordinatorDispatchResult:
        self.calls.append((job_id, request))
        return CoordinatorDispatchResult(
            responses=[
                _specialist_response(
                    job_id=job_id,
                    node_role="regime",
                    peer_id="peer-regime-test",
                    summary="Regime supports upside.",
                    signals=["Positive liquidity regime"],
                    risks=[],
                    scenario_view=ScenarioView(bull=0.45, base=0.35, bear=0.2),
                ),
                _specialist_response(
                    job_id=job_id,
                    node_role="narrative",
                    peer_id="peer-narrative-test",
                    summary="ETF narrative remains active.",
                    signals=["ETF flows remain constructive"],
                    risks=[],
                    scenario_view=ScenarioView(bull=0.4, base=0.4, bear=0.2),
                ),
                _specialist_response(
                    job_id=job_id,
                    node_role="risk",
                    peer_id="peer-risk-test",
                    summary="Break below support invalidates the thesis.",
                    signals=[],
                    risks=["Macro volatility can pressure beta assets"],
                    scenario_view=ScenarioView(bull=0.3, base=0.45, bear=0.25),
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
            run_metadata={
                "run_mode": "live-axl",
                "expected_roles": ["regime", "narrative", "risk"],
                "completed_roles": ["regime", "narrative", "risk"],
                "missing_roles": [],
            },
        )


class FailingLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        raise RuntimeError("force fallback path")


class StubChainReceiptService:
    async def record_job_receipts(
        self,
        *,
        job_id: str,
        request: ThesisRequest,
        dispatch_result: CoordinatorDispatchResult,
        memo: object,
    ) -> JobChainReceipts:
        return JobChainReceipts(
            receipt_status="confirmed",
            receipts=[
                ChainReceipt.confirmed(
                    kind="task",
                    tx_hash="0x" + "aa" * 32,
                    explorer_base_url="https://gensyn-testnet.explorer.alchemy.com",
                ),
                *[
                    ChainReceipt.confirmed(
                        kind="contribution",
                        role=response.node_role,
                        tx_hash=f"0x{index:064x}",
                        explorer_base_url=(
                            "https://gensyn-testnet.explorer.alchemy.com"
                        ),
                    )
                    for index, response in enumerate(
                        dispatch_result.responses,
                        start=1,
                    )
                ],
            ],
        )


def _specialist_response(
    job_id: str,
    node_role: str,
    peer_id: str,
    summary: str,
    signals: list[str],
    risks: list[str],
    scenario_view: ScenarioView,
) -> SpecialistResponse:
    return SpecialistResponse(
        job_id=job_id,
        node_role=node_role,
        peer_id=peer_id,
        summary=summary,
        scenario_view=scenario_view,
        signals=signals,
        risks=risks,
        confidence=0.7,
        citations=[],
        timestamp="2026-04-23T00:00:00Z",
    )


def _configure_test_store(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    app.state.job_store = JobStore(database_url=database_url)
    app.state.coordinator_service = StubCoordinator()
    app.state.memo_synthesis_service = MemoSynthesisService(
        llm_client=FailingLLMClient()
    )
    if hasattr(app.state, "chain_receipt_service"):
        delattr(app.state, "chain_receipt_service")
    asyncio.run(app.state.job_store.initialize())


def test_create_job_returns_job_id_and_status(tmp_path: Path) -> None:
    _configure_test_store(tmp_path)

    async def _exercise() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/jobs",
                json={
                    "thesis": "ETH can rally on improving ETF flows.",
                    "asset": "ETH",
                    "horizon_days": 30,
                },
            )

    response = asyncio.run(_exercise())

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert UUID(payload["job_id"])
    coordinator = app.state.coordinator_service
    assert len(coordinator.calls) == 1
    assert coordinator.calls[0][0] == payload["job_id"]


def test_get_job_returns_persisted_result(tmp_path: Path) -> None:
    _configure_test_store(tmp_path)

    async def _exercise() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            create_response = await client.post(
                "/jobs",
                json={
                    "thesis": "BTC remains range-bound until macro volatility fades.",
                    "asset": "BTC",
                    "horizon_days": 14,
                },
            )
            job_id = create_response.json()["job_id"]
            get_response = await client.get(f"/jobs/{job_id}")
            return create_response, get_response

    create_response, get_response = asyncio.run(_exercise())
    job_id = create_response.json()["job_id"]

    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["job_id"] == job_id
    assert payload["status"] == "completed"
    assert payload["payload"] == {
        "thesis": "BTC remains range-bound until macro volatility fades.",
        "asset": "BTC",
        "horizon_days": 14,
    }
    assert payload["memo"]["job_id"] == job_id
    assert payload["memo"]["normalized_thesis"] == (
        "Will BTC validate this thesis over 14 days: "
        "BTC remains range-bound until macro volatility fades."
    )
    assert payload["memo"]["partial"] is False
    assert payload["memo"]["provenance"] == [
        {
            "node_role": "regime",
            "peer_id": "peer-regime-test",
            "timestamp": "2026-04-23T00:00:00Z",
        },
        {
            "node_role": "narrative",
            "peer_id": "peer-narrative-test",
            "timestamp": "2026-04-23T00:00:00Z",
        },
        {
            "node_role": "risk",
            "peer_id": "peer-risk-test",
            "timestamp": "2026-04-23T00:00:00Z",
        },
    ]
    assert payload["memo"]["catalysts"] == [
        "Positive liquidity regime",
        "ETF flows remain constructive",
    ]
    assert payload["memo"]["risks"] == ["Macro volatility can pressure beta assets"]
    assert payload["memo"]["invalidation_triggers"] == [
        "Break below support invalidates the thesis."
    ]
    assert payload["run_metadata"]["run_mode"] == "live-axl"
    assert payload["run_metadata"]["completed_roles"] == [
        "regime",
        "narrative",
        "risk",
    ]


def test_job_persists_chain_receipts(tmp_path: Path) -> None:
    _configure_test_store(tmp_path)
    app.state.chain_receipt_service = StubChainReceiptService()

    async def _exercise() -> dict[str, object]:
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
            return (await client.get(f"/jobs/{job_id}")).json()

    payload = asyncio.run(_exercise())
    run_metadata = payload["run_metadata"]

    assert run_metadata["receipt_status"] == "confirmed"
    assert run_metadata["chain_receipts"] == [
        {
            "kind": "task",
            "status": "confirmed",
            "tx_hash": "0x" + "aa" * 32,
            "explorer_url": (
                "https://gensyn-testnet.explorer.alchemy.com/tx/" + "0x" + "aa" * 32
            ),
        },
        {
            "kind": "contribution",
            "status": "confirmed",
            "tx_hash": "0x" + "01".zfill(64),
            "explorer_url": (
                "https://gensyn-testnet.explorer.alchemy.com/tx/"
                + "0x"
                + "01".zfill(64)
            ),
            "role": "regime",
        },
        {
            "kind": "contribution",
            "status": "confirmed",
            "tx_hash": "0x" + "02".zfill(64),
            "explorer_url": (
                "https://gensyn-testnet.explorer.alchemy.com/tx/"
                + "0x"
                + "02".zfill(64)
            ),
            "role": "narrative",
        },
        {
            "kind": "contribution",
            "status": "confirmed",
            "tx_hash": "0x" + "03".zfill(64),
            "explorer_url": (
                "https://gensyn-testnet.explorer.alchemy.com/tx/"
                + "0x"
                + "03".zfill(64)
            ),
            "role": "risk",
        },
    ]


def test_reputation_endpoint_returns_local_projection(tmp_path: Path) -> None:
    _configure_test_store(tmp_path)

    async def _exercise() -> dict[str, object]:
        job = await app.state.job_store.create_job(
            ThesisRequest(
                thesis="ETH can rally on improving ETF flows.",
                asset="ETH",
                horizon_days=30,
            )
        )
        memo = await MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
            job_id=job.job_id,
            request=ThesisRequest(
                thesis="ETH can rally on improving ETF flows.",
                asset="ETH",
                horizon_days=30,
            ),
            dispatch_result=CoordinatorDispatchResult(
                responses=[],
                topology_snapshot={},
                market_snapshot={},
                news_headlines=[],
            ),
        )
        await app.state.job_store.complete_job(
            job_id=job.job_id,
            memo=memo,
            run_metadata={
                "reputation_updates": [
                    update.to_dict()
                    for update in build_reputation_updates(
                        [
                            VerificationAttestation(
                                job_id=job.job_id,
                                node_role="regime",
                                peer_id="peer-regime-test",
                                status="accepted",
                                score=0.9,
                            )
                        ]
                    )
                ]
            },
        )
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return (await client.get("/reputation")).json()

    payload = asyncio.run(_exercise())

    assert payload == {
        "leaderboard": [
            {
                "node_role": "regime",
                "peer_id": "peer-regime-test",
                "reputation_points": 90.0,
                "accepted_contributions": 1,
                "rejected_contributions": 0,
                "total_verifier_score": 0.9,
            }
        ]
    }
