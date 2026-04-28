"""Application entrypoint for Signal Count."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.pages import router as pages_router
from app.axl.client import AXLClient
from app.axl.registry import AXLRegistry
from app.chain.broadcaster import GensynReceiptRecorder
from app.chain.config import ChainConfig
from app.config.settings import get_settings
from app.coordinator.service import CoordinatorService
from app.coordinator.synthesis import MemoSynthesisService
from app.demo.offline_transport import OfflineDemoAXLTransport
from app.integrations.demo_llm_client import DemoLLMClient
from app.integrations.llm_client import LLMClient
from app.integrations.market_data import MarketDataProvider
from app.integrations.news_feed import NewsFeedProvider
from app.nodes.verifier.service import VerifierService
from app.store import JobStore


def create_app() -> FastAPI:
    settings = get_settings()
    registry = AXLRegistry(settings)
    llm_client = DemoLLMClient() if settings.signal_count_demo_llm else LLMClient()
    axl_transport = (
        OfflineDemoAXLTransport(settings=settings, registry=registry)
        if settings.signal_count_offline_demo
        else AXLClient(settings=settings, registry=registry)
    )

    app = FastAPI(title="Signal Count")
    app.state.job_store = JobStore()
    app.state.memo_synthesis_service = MemoSynthesisService(llm_client=llm_client)
    app.state.coordinator_service = CoordinatorService(
        axl_client=axl_transport,
        registry=registry,
        market_data_provider=MarketDataProvider(),
        news_feed_provider=NewsFeedProvider(),
        llm_client=llm_client,
        verifier=VerifierService(verifier_private_key=settings.verifier_private_key),
    )
    if (
        settings.signal_count_chain_receipts
        and not settings.signal_count_offline_demo
        and settings.chain_writer_private_key
    ):
        app.state.chain_receipt_service = GensynReceiptRecorder(
            config=ChainConfig.from_settings(settings)
        )
    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(pages_router)
    return app


app = create_app()
