"""AXL-facing specialist node server."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, status

from app.axl.registry import AXLRegistry
from app.config.settings import Settings, get_settings
from app.integrations.demo_llm_client import DemoLLMClient
from app.integrations.llm_client import LLMClient
from app.nodes.narrative.service import NarrativeService
from app.nodes.regime.service import RegimeService, RegimeSnapshot
from app.nodes.risk.service import RiskService
from app.ree.runner import ReeRunner
from app.schemas.contracts import SpecialistResponse


def create_node_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    registry = AXLRegistry(resolved_settings)
    service_name = _resolve_service_name(resolved_settings, registry)
    service_endpoint = f"{resolved_settings.node_public_url.rstrip('/')}/mcp"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.registry = registry
        app.state.service_name = service_name
        app.state.service_endpoint = service_endpoint
        app.state.llm_client = (
            DemoLLMClient() if resolved_settings.signal_count_demo_llm else LLMClient()
        )
        await register_with_router(
            router_url=resolved_settings.axl_mcp_router_url,
            service_name=service_name,
            service_endpoint=service_endpoint,
        )
        try:
            yield
        finally:
            await deregister_from_router(
                router_url=resolved_settings.axl_mcp_router_url,
                service_name=service_name,
            )

    app = FastAPI(
        title=f"Signal Count {resolved_settings.node_role} node", lifespan=lifespan
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "role": resolved_settings.node_role,
            "service": service_name,
        }

    @app.post("/mcp")
    async def mcp(payload: dict[str, Any]) -> dict[str, Any]:
        response = await analyze_payload(
            payload=payload,
            settings=resolved_settings,
            registry=registry,
            llm_client=app.state.llm_client,
        )
        return response.model_dump(mode="json")

    return app


async def analyze_payload(
    *,
    payload: dict[str, Any],
    settings: Settings,
    registry: AXLRegistry,
    llm_client: LLMClient,
) -> SpecialistResponse:
    role = str(payload.get("role") or settings.node_role)
    job_id = str(payload.get("job_id") or "")
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="job_id is required",
        )

    try:
        peer_id = registry.get_service_for_role(role).peer_id
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    if role == "regime":
        snapshot = payload.get("snapshot", {})
        if not isinstance(snapshot, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="snapshot must be an object",
            )
        return RegimeService(settings=settings).analyze(
            job_id=job_id,
            snapshot=RegimeSnapshot(
                price_return=float(snapshot.get("price_return", 0.0)),
                volatility=float(snapshot.get("volatility", 0.20)),
            ),
        )

    if role == "narrative":
        headlines = payload.get("headlines", [])
        if not isinstance(headlines, list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="headlines must be a list",
            )
        return await NarrativeService(llm_client=llm_client, settings=settings).analyze(
            job_id=job_id,
            peer_id=peer_id,
            headlines=[str(item) for item in headlines],
        )

    if role == "risk":
        ree_runner = (
            ReeRunner(
                command=settings.gensyn_sdk_command,
                cpu_only=settings.ree_cpu_only,
            )
            if settings.signal_count_ree_enabled
            else None
        )
        return await RiskService(
            llm_client=llm_client, settings=settings, ree_runner=ree_runner
        ).analyze(
            job_id=job_id,
            peer_id=peer_id,
            thesis=str(payload.get("thesis", "")),
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=f"Unsupported node role: {role}",
    )


async def register_with_router(
    *,
    router_url: str,
    service_name: str,
    service_endpoint: str,
) -> None:
    await asyncio.to_thread(
        _request_json,
        f"{router_url.rstrip('/')}/register",
        "POST",
        {"service": service_name, "endpoint": service_endpoint},
    )


async def deregister_from_router(*, router_url: str, service_name: str) -> None:
    try:
        await asyncio.to_thread(
            _request_json,
            f"{router_url.rstrip('/')}/register/{service_name}",
            "DELETE",
            None,
        )
    except RuntimeError:
        pass


def _resolve_service_name(settings: Settings, registry: AXLRegistry) -> str:
    if settings.node_service_name:
        return settings.node_service_name
    return registry.get_service_for_role(settings.node_role).service_name


def _request_json(url: str, method: str, payload: dict[str, str] | None) -> None:
    request = Request(
        url,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(request, timeout=5):  # noqa: S310
            return
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AXL MCP router {method} failed: {url}") from exc


app = create_node_app()
