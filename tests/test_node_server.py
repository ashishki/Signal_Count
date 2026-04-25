import asyncio

from fastapi import HTTPException

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.nodes.server import analyze_payload, create_node_app


class StubLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        if "risk specialist" in messages[0]["content"]:
            return """
            {
              "summary": "Risk case is elevated if flows weaken.",
              "counter_thesis": "Flows may already be priced in.",
              "risks": ["ETF flows reverse", "liquidity tightens"],
              "invalidation_triggers": ["negative flows", "support break"],
              "scenario_view": {"bull": 0.25, "base": 0.35, "bear": 0.40},
              "confidence": 0.7
            }
            """
        return """
        {
          "summary": "Narrative is constructive but flow-dependent.",
          "catalysts": ["ETF flows improve"],
          "unknowns": ["macro liquidity"],
          "scenario_framing": ["base case remains intact"],
          "scenario_view": {"bull": 0.4, "base": 0.4, "bear": 0.2},
          "confidence": 0.6
        }
        """


def test_node_app_exposes_health_route_without_starting_lifespan() -> None:
    settings = Settings(node_role="risk", node_service_name="risk_analyst")
    app = create_node_app(settings)

    assert app.title == "Signal Count risk node"


def test_analyze_payload_handles_regime_role() -> None:
    settings = Settings(node_role="regime")
    response = asyncio.run(
        analyze_payload(
            payload={
                "job_id": "job-node-1",
                "role": "regime",
                "snapshot": {"price_return": 0.08, "volatility": 0.18},
            },
            settings=settings,
            registry=AXLRegistry(settings),
            llm_client=StubLLMClient(),
        )
    )

    assert response.node_role == "regime"
    assert response.peer_id == "peer-regime-example"
    assert response.job_id == "job-node-1"


def test_analyze_payload_handles_narrative_role() -> None:
    settings = Settings(node_role="narrative")
    response = asyncio.run(
        analyze_payload(
            payload={
                "job_id": "job-node-2",
                "role": "narrative",
                "headlines": ["ETF flows improve"],
            },
            settings=settings,
            registry=AXLRegistry(settings),
            llm_client=StubLLMClient(),
        )
    )

    assert response.node_role == "narrative"
    assert response.signals[0] == "catalyst: ETF flows improve"


def test_analyze_payload_handles_risk_role() -> None:
    settings = Settings(node_role="risk")
    response = asyncio.run(
        analyze_payload(
            payload={
                "job_id": "job-node-3",
                "role": "risk",
                "thesis": "ETH can rally on ETF flows.",
            },
            settings=settings,
            registry=AXLRegistry(settings),
            llm_client=StubLLMClient(),
        )
    )

    assert response.node_role == "risk"
    assert "risk: ETF flows reverse" in response.risks


def test_analyze_payload_rejects_missing_job_id() -> None:
    settings = Settings(node_role="risk")

    try:
        asyncio.run(
            analyze_payload(
                payload={"role": "risk"},
                settings=settings,
                registry=AXLRegistry(settings),
                llm_client=StubLLMClient(),
            )
        )
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail == "job_id is required"
    else:
        raise AssertionError("Expected HTTPException")
