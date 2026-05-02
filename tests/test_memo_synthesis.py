import asyncio
import json
from dataclasses import replace

from app.coordinator.service import CoordinatorDispatchResult
from app.coordinator import synthesis as synthesis_module
from app.coordinator.synthesis import MemoSynthesisService
from app.observability.metrics import NoopMetrics
from app.rendering.memo import render_memo_markdown
from app.schemas.contracts import (
    FinalMemo,
    ScenarioView,
    SpecialistResponse,
    ThesisRequest,
    VerificationAttestation,
)


class StubLLMClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        self.calls.append((model, messages))
        return json.dumps(self.payload)


def test_synthesis_returns_schema_valid_final_memo() -> None:
    metrics = NoopMetrics()
    dispatch_result = _dispatch_result(job_id="job-synthesis-1")
    llm_client = StubLLMClient(
        {
            "job_id": "ignored-by-service",
            "normalized_thesis": "ignored-by-service",
            "scenarios": {"bull": 0.38, "base": 0.42, "bear": 0.20},
            "supporting_evidence": ["Regime and narrative both support upside."],
            "opposing_evidence": ["Risk specialist flags support break."],
            "catalysts": [
                "Regime liquidity supports upside.",
                "ETF flow narrative remains constructive.",
            ],
            "risks": [
                "Macro volatility can pressure beta assets.",
                "Risk specialist sees a support break as the key failure path.",
            ],
            "invalidation_triggers": ["ETH loses the key support range."],
            "confidence_rationale": "All specialists responded with moderate confidence.",
            "provenance": [],
            "partial": True,
            "partial_reason": "ignored-by-service",
        }
    )
    original_get_metrics = synthesis_module.get_metrics
    synthesis_module.get_metrics = lambda: metrics

    try:
        memo = asyncio.run(
            MemoSynthesisService(llm_client=llm_client, model="test-model").synthesize(
                job_id="job-synthesis-1",
                request=ThesisRequest(
                    thesis="ETH can rally on improving ETF flows.",
                    asset="ETH",
                    horizon_days=30,
                ),
                dispatch_result=dispatch_result,
            )
        )
    finally:
        synthesis_module.get_metrics = original_get_metrics

    assert isinstance(memo, FinalMemo)
    assert memo.job_id == "job-synthesis-1"
    assert memo.normalized_thesis == (
        "Will ETH validate this thesis over 30 days: "
        "ETH can rally on improving ETF flows."
    )
    assert memo.scenarios == ScenarioView(bull=0.38, base=0.42, bear=0.20)
    assert memo.supporting_evidence == ["Regime and narrative both support upside."]
    assert memo.opposing_evidence == ["Risk specialist flags support break."]
    assert (
        memo.confidence_rationale
        == "All specialists responded with moderate confidence."
    )
    assert memo.partial is False
    assert memo.partial_reason is None
    assert llm_client.calls[0][0] == "test-model"
    assert "job_id: job-synthesis-1" in llm_client.calls[0][1][1]["content"]
    assert "job_id: placeholder" not in llm_client.calls[0][1][1]["content"]
    assert metrics.counter_events[0].labels["outcome"] == "success"
    assert metrics.histogram_events[0].name == "memo_synthesis_latency_ms"


def test_synthesis_preserves_per_node_provenance() -> None:
    dispatch_result = _dispatch_result(job_id="job-synthesis-2")
    llm_client = StubLLMClient(
        {
            "job_id": "job-synthesis-2",
            "normalized_thesis": "Will BTC validate this thesis?",
            "scenarios": {"bull": 0.25, "base": 0.50, "bear": 0.25},
            "supporting_evidence": ["Constructive liquidity regime."],
            "opposing_evidence": ["Narrative disagreement remains unresolved."],
            "catalysts": ["Constructive liquidity regime."],
            "risks": ["Narrative disagreement remains unresolved."],
            "invalidation_triggers": ["BTC breaks the invalidation level."],
            "confidence_rationale": "Mixed specialist evidence.",
            "provenance": [
                {
                    "node_role": "llm-invented",
                    "peer_id": "not-a-real-peer",
                    "timestamp": "2026-04-22T00:00:00Z",
                }
            ],
            "partial": False,
            "partial_reason": None,
        }
    )

    memo = asyncio.run(
        MemoSynthesisService(llm_client=llm_client).synthesize(
            job_id="job-synthesis-2",
            request=ThesisRequest(
                thesis="BTC remains supported by liquidity.",
                asset="BTC",
                horizon_days=14,
            ),
            dispatch_result=dispatch_result,
        )
    )

    assert [record.model_dump() for record in memo.provenance] == [
        {
            "node_role": "regime",
            "peer_id": "peer-regime-test",
            "timestamp": "2026-04-23T00:00:00Z",
        },
        {
            "node_role": "narrative",
            "peer_id": "peer-narrative-test",
            "timestamp": "2026-04-23T00:01:00Z",
        },
        {
            "node_role": "risk",
            "peer_id": "peer-risk-test",
            "timestamp": "2026-04-23T00:02:00Z",
        },
    ]


def test_synthesis_records_fallback_metrics() -> None:
    metrics = NoopMetrics()
    original_get_metrics = synthesis_module.get_metrics
    synthesis_module.get_metrics = lambda: metrics

    class FailingLLMClient:
        async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
            raise RuntimeError("force fallback path")

    try:
        memo = asyncio.run(
            MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
                job_id="job-synthesis-fallback",
                request=ThesisRequest(
                    thesis="ETH remains supported by liquidity.",
                    asset="ETH",
                    horizon_days=21,
                ),
                dispatch_result=_dispatch_result(job_id="job-synthesis-fallback"),
            )
        )
    finally:
        synthesis_module.get_metrics = original_get_metrics

    assert memo.partial is False
    assert memo.supporting_evidence
    assert memo.opposing_evidence
    assert memo.confidence_rationale.startswith("Average specialist confidence")
    assert metrics.counter_events[0].labels["outcome"] == "fallback"
    assert metrics.histogram_events[0].name == "memo_synthesis_latency_ms"


def test_rejected_specialist_output_is_visible() -> None:
    dispatch_result = _dispatch_result_with_rejected_response(
        job_id="job-synthesis-rejected"
    )

    class FailingLLMClient:
        async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
            raise RuntimeError("force fallback path")

    memo = asyncio.run(
        MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
            job_id="job-synthesis-rejected",
            request=ThesisRequest(
                thesis="ETH remains supported by liquidity.",
                asset="ETH",
                horizon_days=21,
            ),
            dispatch_result=dispatch_result,
        )
    )

    assert memo.partial is True
    assert memo.partial_reason == "Rejected specialist roles: risk"
    assert memo.verification_attestations[0].status == "rejected"
    assert any(
        item.startswith("Rejected risk output from peer-risk-test")
        for item in memo.opposing_evidence
    )


def test_memo_surfaces_source_quality_and_disagreement() -> None:
    dispatch_result = replace(
        _dispatch_result(job_id="job-source-quality"),
        input_sources=[
            {
                "input_role": "regime",
                "input_name": "market_snapshot",
                "source_quality": "fixture source",
                "source_url": "fixture://signal-count/market-snapshot/v1/ETH",
                "retrieved_at": "2026-05-01T00:00:00Z",
                "source_hash": "0x" + ("a" * 64),
            },
            {
                "input_role": "narrative",
                "input_name": "news_headline",
                "source_quality": "fixture source",
                "source_url": "fixture://signal-count/news-headline/v1/ETH/1",
                "retrieved_at": "2026-05-01T00:00:01Z",
                "source_hash": "0x" + ("b" * 64),
            },
        ],
    )

    class FailingLLMClient:
        async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
            raise RuntimeError("force fallback path")

    memo = asyncio.run(
        MemoSynthesisService(llm_client=FailingLLMClient()).synthesize(
            job_id="job-source-quality",
            request=ThesisRequest(
                thesis=("ETH upside depends on liquidity but fails if support breaks."),
                asset="ETH",
                horizon_days=21,
            ),
            dispatch_result=dispatch_result,
        )
    )
    rendered = render_memo_markdown(memo)

    assert any(
        source.source_quality == "fixture source" for source in memo.evidence_sources
    )
    assert any(
        source.source_hash == "0x" + ("a" * 64) for source in memo.evidence_sources
    )
    assert any("support invalidates" in item for item in memo.opposing_evidence)
    assert "## Source Quality" in rendered
    assert "fixture source" in rendered


def _dispatch_result(job_id: str) -> CoordinatorDispatchResult:
    return CoordinatorDispatchResult(
        responses=[
            _specialist_response(
                job_id=job_id,
                node_role="regime",
                peer_id="peer-regime-test",
                timestamp="2026-04-23T00:00:00Z",
                summary="Liquidity regime supports upside.",
                signals=["Regime liquidity supports upside."],
                risks=[],
                scenario_view=ScenarioView(bull=0.45, base=0.35, bear=0.20),
            ),
            _specialist_response(
                job_id=job_id,
                node_role="narrative",
                peer_id="peer-narrative-test",
                timestamp="2026-04-23T00:01:00Z",
                summary="ETF flow narrative remains constructive.",
                signals=["ETF flow narrative remains constructive."],
                risks=["Narrative can cool if flows reverse."],
                scenario_view=ScenarioView(bull=0.40, base=0.40, bear=0.20),
            ),
            _specialist_response(
                job_id=job_id,
                node_role="risk",
                peer_id="peer-risk-test",
                timestamp="2026-04-23T00:02:00Z",
                summary="A break below support invalidates the thesis.",
                signals=["invalidation: support break"],
                risks=["Macro volatility can pressure beta assets."],
                scenario_view=ScenarioView(bull=0.30, base=0.45, bear=0.25),
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
    )


def _dispatch_result_with_rejected_response(job_id: str) -> CoordinatorDispatchResult:
    rejected = _specialist_response(
        job_id=job_id,
        node_role="risk",
        peer_id="peer-risk-test",
        timestamp="2026-04-23T00:02:00Z",
        summary="A break below support invalidates the thesis.",
        signals=["invalidation: support break"],
        risks=["Macro volatility can pressure beta assets."],
        scenario_view=ScenarioView(bull=0.30, base=0.45, bear=0.25),
    )
    result = _dispatch_result(job_id=job_id)
    return replace(
        result,
        responses=[
            response for response in result.responses if response.node_role != "risk"
        ],
        rejected_responses=[rejected],
        verification_attestations=[
            VerificationAttestation(
                job_id=job_id,
                node_role="risk",
                peer_id="peer-risk-test",
                status="rejected",
                score=0.31,
                reasons=["invalid_signature"],
            )
        ],
        partial=True,
    )


def _specialist_response(
    job_id: str,
    node_role: str,
    peer_id: str,
    timestamp: str,
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
        timestamp=timestamp,
    )
