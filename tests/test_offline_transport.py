import asyncio

import pytest

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.coordinator.service import CoordinatorService
from app.demo.offline_transport import OfflineDemoAXLTransport
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_feed import NewsFeedProvider
from app.schemas.contracts import ThesisRequest


def test_offline_transport_can_force_role_timeout() -> None:
    settings = Settings(signal_count_offline_fail_role="risk")
    transport = OfflineDemoAXLTransport(
        settings=settings, registry=AXLRegistry(settings)
    )

    with pytest.raises(TimeoutError, match="risk timeout"):
        asyncio.run(
            transport.dispatch_specialist(
                peer_id="peer-risk-example",
                service_name="risk_analyst",
                payload={
                    "job_id": "job-offline-partial",
                    "role": "risk",
                    "thesis": "ETH can rally on ETF flows.",
                },
            )
        )


def test_offline_transport_reports_preview_metadata() -> None:
    settings = Settings()
    transport = OfflineDemoAXLTransport(
        settings=settings, registry=AXLRegistry(settings)
    )

    assert transport.run_metadata() == {
        "transport": "offline-preview",
        "run_mode": "offline-demo-preview",
        "axl_local_base_url": "http://127.0.0.1:9002",
        "axl_mcp_router_url": "http://127.0.0.1:9003",
    }


def test_offline_partial_preview_marks_missing_role() -> None:
    settings = Settings(signal_count_offline_fail_role="risk")
    registry = AXLRegistry(settings)
    service = CoordinatorService(
        axl_client=OfflineDemoAXLTransport(settings=settings, registry=registry),
        registry=registry,
        market_data_provider=MarketDataProvider(),
        news_feed_provider=NewsFeedProvider(),
        llm_client=object(),
    )

    result = asyncio.run(
        service.dispatch(
            job_id="job-offline-partial",
            request=ThesisRequest(
                thesis="ETH can rally on ETF flows.",
                asset="ETH",
                horizon_days=30,
            ),
        )
    )

    assert result.partial is True
    assert result.missing_roles == ["risk"]
    assert result.run_metadata["run_mode"] == "offline-demo-preview"
    assert result.run_metadata["missing_roles"] == ["risk"]
    assert any(
        record.node_role == "risk" and record.status == "timed_out"
        for record in result.node_execution_records
    )
