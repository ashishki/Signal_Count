import asyncio
import json

from app.config.settings import Settings
from app.nodes.narrative.service import NarrativeService
from app.schemas.contracts import SpecialistResponse


class StubLLMClient:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        self.calls.append({"model": model, "messages": messages})
        return self.response_text


def test_narrative_service_returns_valid_specialist_response() -> None:
    stub_client = StubLLMClient(
        json.dumps(
            {
                "summary": "ETF demand and treasury policy headlines keep the market focused on upside catalysts.",
                "catalysts": ["Potential ETF inflows", "Improving regulatory tone"],
                "unknowns": ["Whether flows persist after launch week"],
                "scenario_framing": ["Bull case improves if demand broadens"],
                "scenario_view": {"bull": 0.35, "base": 0.45, "bear": 0.20},
                "confidence": 0.68,
            }
        )
    )
    service = NarrativeService(llm_client=stub_client, settings=Settings())

    response = asyncio.run(
        service.analyze(
            job_id="job-narrative-123",
            peer_id="peer-narrative-example",
            headlines=[
                "Spot ETH ETF optimism lifts crypto sentiment",
                "Macro data keeps rate-cut expectations in focus",
            ],
        )
    )

    assert isinstance(response, SpecialistResponse)
    assert response.job_id == "job-narrative-123"
    assert response.node_role == "narrative"
    assert response.peer_id == "peer-narrative-example"
    assert response.summary
    assert any(signal.startswith("catalyst: ") for signal in response.signals)
    assert response.confidence == 0.68
    total = (
        response.scenario_view.bull
        + response.scenario_view.base
        + response.scenario_view.bear
    )
    assert total == 1.0
    assert stub_client.calls


def test_narrative_service_emits_catalysts_and_unknowns() -> None:
    stub_client = StubLLMClient(
        json.dumps(
            {
                "summary": "Headlines point to a constructive but still event-driven setup.",
                "catalysts": ["Short-covering after strong ETF headlines"],
                "unknowns": ["No clear read on how durable the move is"],
                "scenario_framing": ["Base case remains choppy upside"],
                "scenario_view": {"bull": 0.40, "base": 0.40, "bear": 0.20},
                "confidence": 0.55,
            }
        )
    )
    service = NarrativeService(llm_client=stub_client, settings=Settings())

    response = asyncio.run(
        service.analyze(
            job_id="job-narrative-456",
            peer_id="peer-narrative-example",
            headlines=["ETH rallies as headline momentum improves"],
        )
    )

    assert any(signal.startswith("catalyst: ") for signal in response.signals)
    assert any(risk.startswith("unknown: ") for risk in response.risks)


def test_narrative_service_raises_value_error_for_non_json_response() -> None:
    stub_client = StubLLMClient("not json")
    service = NarrativeService(llm_client=stub_client, settings=Settings())

    try:
        asyncio.run(
            service.analyze(
                job_id="job-narrative-invalid-json",
                peer_id="peer-narrative-example",
                headlines=["Headline text"],
            )
        )
    except ValueError as exc:
        assert str(exc) == "LLM response is not valid JSON"
    else:
        raise AssertionError("Expected ValueError for invalid JSON response")


def test_narrative_service_uses_safe_default_for_missing_summary() -> None:
    stub_client = StubLLMClient(
        json.dumps(
            {
                "catalysts": ["Headline catalyst"],
                "unknowns": ["Open question"],
                "scenario_framing": ["Base case remains mixed"],
                "scenario_view": {"bull": 0.30, "base": 0.50, "bear": 0.20},
                "confidence": 0.5,
            }
        )
    )
    service = NarrativeService(llm_client=stub_client, settings=Settings())

    response = asyncio.run(
        service.analyze(
            job_id="job-narrative-missing-summary",
            peer_id="peer-narrative-example",
            headlines=["Headline text"],
        )
    )

    assert response.summary == "Narrative context is mixed."
