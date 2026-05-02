import asyncio

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.coordinator.service import CoordinatorService
from app.coordinator.synthesis import MemoSynthesisService
from app.schemas.contracts import ScenarioView, SpecialistResponse, ThesisRequest


class TimeoutAXLClient:
    def __init__(self, timed_out_role: str) -> None:
        self.timed_out_role = timed_out_role

    async def fetch_topology(self) -> dict[str, object]:
        return {
            "local_peer_id": "peer-coordinator-test",
            "peers": [
                "peer-regime-example",
                "peer-narrative-example",
                "peer-risk-example",
            ],
        }

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, object],
    ) -> SpecialistResponse:
        role = str(payload["role"])
        if role == self.timed_out_role:
            raise TimeoutError(f"{role} timed out")

        return SpecialistResponse(
            job_id=str(payload["job_id"]),
            node_role=role,
            peer_id=peer_id,
            summary=f"{role} summary",
            scenario_view=ScenarioView(bull=0.4, base=0.4, bear=0.2),
            signals=[f"{role} signal"],
            risks=[f"{role} risk"] if role != "regime" else [],
            confidence=0.7,
            citations=[],
            timestamp="2026-04-24T00:00:00Z",
        )


class StubMarketDataProvider:
    async def fetch_snapshot(self, request: ThesisRequest) -> dict[str, float]:
        return {"price_return": 0.05, "volatility": 0.18}


class StubNewsFeedProvider:
    async def fetch_headlines(self, request: ThesisRequest) -> list[str]:
        return ["ETF flows remain constructive"]


class FailingLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        raise RuntimeError("force fallback path")


def test_coordinator_returns_partial_memo_when_one_specialist_times_out() -> None:
    request = ThesisRequest(
        thesis="ETH can extend higher on improving flows.",
        asset="ETH",
        horizon_days=30,
    )
    dispatch_result = asyncio.run(
        _service(timed_out_role="risk").dispatch(
            job_id="job-partial-1",
            request=request,
        )
    )

    memo = asyncio.run(
        MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
            job_id="job-partial-1",
            request=request,
            dispatch_result=dispatch_result,
        )
    )

    assert dispatch_result.partial is True
    assert dispatch_result.missing_roles == ["risk"]
    assert any(
        record.node_role == "risk" and record.status == "timed_out"
        for record in dispatch_result.node_execution_records
    )
    assert memo.partial is True
    assert memo.partial_reason == "Missing specialist roles: risk"


def test_partial_memo_names_missing_node_without_fabrication() -> None:
    request = ThesisRequest(
        thesis="ETH stays supported while liquidity remains stable.",
        asset="ETH",
        horizon_days=14,
    )
    dispatch_result = asyncio.run(
        _service(timed_out_role="risk").dispatch(
            job_id="job-partial-2",
            request=request,
        )
    )

    memo = asyncio.run(
        MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
            job_id="job-partial-2",
            request=request,
            dispatch_result=dispatch_result,
        )
    )

    assert memo.partial is True
    assert memo.partial_reason == "Missing specialist roles: risk"
    assert {record.node_role for record in memo.provenance} == {
        "regime",
        "narrative",
    }
    assert memo.invalidation_triggers == []


def test_peer_fallback_is_auditable() -> None:
    request = ThesisRequest(
        thesis="ETH stays supported while liquidity remains stable.",
        asset="ETH",
        horizon_days=14,
    )
    dispatch_result = asyncio.run(
        _service(timed_out_role="risk").dispatch(
            job_id="job-partial-selection",
            request=request,
        )
    )

    risk_record = next(
        record
        for record in dispatch_result.node_execution_records
        if record.node_role == "risk"
    )
    assert risk_record.status == "timed_out"
    assert risk_record.selection_reason == "capability:topology-up"
    assert dispatch_result.run_metadata["peer_selection"][-1] == {
        "node_role": "risk",
        "peer_id": "peer-risk-example",
        "selection_reason": "capability:topology-up",
    }


def test_failed_peer_candidates_are_all_audited() -> None:
    request = ThesisRequest(
        thesis="ETH stays supported while liquidity remains stable.",
        asset="ETH",
        horizon_days=14,
    )
    service = CoordinatorService(
        axl_client=TimeoutAXLClient(timed_out_role="risk"),
        registry=AXLRegistry(
            Settings(
                risk_peer_candidates="peer-risk-a:risk_analyst,peer-risk-b:risk_analyst"
            )
        ),
        market_data_provider=StubMarketDataProvider(),
        news_feed_provider=StubNewsFeedProvider(),
        llm_client=object(),
    )

    dispatch_result = asyncio.run(
        service.dispatch(job_id="job-all-risk-candidates-fail", request=request)
    )

    risk_record = next(
        record
        for record in dispatch_result.node_execution_records
        if record.node_role == "risk"
    )
    assert dispatch_result.partial is True
    assert dispatch_result.missing_roles == ["risk"]
    assert risk_record.status == "timed_out"
    assert risk_record.peer_id == "peer-risk-b"
    assert risk_record.attempted_peer_ids == ["peer-risk-a", "peer-risk-b"]
    assert risk_record.selection_reason == (
        "capability:topology-missing; fallback_from=peer-risk-a; "
        "attempts_exhausted=peer-risk-a,peer-risk-b"
    )


def _service(*, timed_out_role: str) -> CoordinatorService:
    return CoordinatorService(
        axl_client=TimeoutAXLClient(timed_out_role=timed_out_role),
        registry=AXLRegistry(Settings()),
        market_data_provider=StubMarketDataProvider(),
        news_feed_provider=StubNewsFeedProvider(),
        llm_client=object(),
    )
