"""Deterministic local-bridge client for AXL routes."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.observability.tracing import get_tracer
from app.schemas.contracts import SpecialistResponse


class AXLClient:
    def __init__(self, settings: Settings, registry: AXLRegistry) -> None:
        self._settings = settings
        self._registry = registry

    def build_mcp_request_path(self, role: str) -> str:
        service = self._registry.get_service_for_role(role)
        return (
            f"{self._settings.axl_local_base_url}"
            f"/mcp/{service.peer_id}/{service.service_name}"
        )

    def build_topology_path(self) -> str:
        return f"{self._settings.axl_local_base_url}{self._settings.axl_topology_path}"

    def run_metadata(self) -> dict[str, object]:
        return {
            "transport": "axl-mcp",
            "axl_local_base_url": self._settings.axl_local_base_url,
            "axl_topology_path": self.build_topology_path(),
            "axl_mcp_router_url": self._settings.axl_mcp_router_url,
        }

    async def fetch_topology(self) -> dict[str, Any]:
        tracer = get_tracer()
        with tracer.span("axl.fetch_topology"):
            return await asyncio.to_thread(
                self._get_json,
                self.build_topology_path(),
            )

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, Any],
    ) -> SpecialistResponse:
        tracer = get_tracer()
        with tracer.span("axl.dispatch_specialist"):
            response = await asyncio.to_thread(
                self._post_json,
                f"{self._settings.axl_local_base_url}/mcp/{peer_id}/{service_name}",
                payload,
            )
        return SpecialistResponse.model_validate(response)

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            with urlopen(url, timeout=10) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("AXL topology request failed") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("AXL topology response must be a JSON object")
        return payload

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(
                request,
                timeout=self._settings.axl_dispatch_timeout_seconds,
            ) as response:  # noqa: S310
                response_payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("AXL specialist dispatch failed") from exc

        if not isinstance(response_payload, dict):
            raise RuntimeError("AXL specialist response must be a JSON object")
        return response_payload
