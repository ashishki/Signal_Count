"""Offline demo transport for local UI capture without a live AXL bridge."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.nodes.regime.service import RegimeService, RegimeSnapshot
from app.schemas.contracts import ScenarioView, SpecialistResponse


class OfflineDemoAXLTransport:
    """Preview transport used only when SIGNAL_COUNT_OFFLINE_DEMO=1."""

    def __init__(self, settings: Settings, registry: AXLRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._regime_service = RegimeService(settings=settings)

    async def fetch_topology(self) -> dict[str, Any]:
        return {
            "mode": "offline-demo-preview",
            "local_peer_id": "offline-coordinator-preview",
            "peers": [
                self._registry.get_service_for_role("regime").peer_id,
                self._registry.get_service_for_role("narrative").peer_id,
                self._registry.get_service_for_role("risk").peer_id,
            ],
        }

    def run_metadata(self) -> dict[str, object]:
        return {
            "transport": "offline-preview",
            "run_mode": "offline-demo-preview",
            "axl_local_base_url": self._settings.axl_local_base_url,
            "axl_mcp_router_url": self._settings.axl_mcp_router_url,
        }

    async def dispatch_specialist(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, Any],
    ) -> SpecialistResponse:
        role = str(payload["role"])
        if role == self._settings.signal_count_offline_fail_role:
            raise TimeoutError(f"offline preview forced {role} timeout")
        if role == "regime":
            snapshot = payload.get("snapshot", {})
            return self._regime_service.analyze(
                job_id=str(payload["job_id"]),
                snapshot=RegimeSnapshot(
                    price_return=float(snapshot.get("price_return", 0.0)),
                    volatility=float(snapshot.get("volatility", 0.20)),
                ),
            )
        if role == "narrative":
            return self._narrative_response(peer_id, service_name, payload)
        if role == "risk":
            return self._risk_response(peer_id, service_name, payload)
        raise ValueError(f"Unknown offline demo role: {role}")

    def _narrative_response(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, Any],
    ) -> SpecialistResponse:
        headlines = [
            str(item)
            for item in payload.get("headlines", [])
            if isinstance(item, str) and item.strip()
        ]
        return SpecialistResponse(
            job_id=str(payload["job_id"]),
            node_role="narrative",
            peer_id=peer_id,
            summary=(
                "Narrative support is constructive but not decisive; the thesis "
                "still depends on flow confirmation and stable liquidity."
            ),
            scenario_view=ScenarioView(bull=0.42, base=0.38, bear=0.20),
            signals=[
                "catalyst: ETF flow improvement would support the upside case.",
                "scenario_frame: stable liquidity keeps the base case intact.",
                f"service: {service_name}",
            ],
            risks=[
                "unknown: headline context is limited in offline preview mode.",
            ],
            confidence=0.62,
            citations=headlines,
            timestamp=_now(),
        )

    def _risk_response(
        self,
        peer_id: str,
        service_name: str,
        payload: dict[str, Any],
    ) -> SpecialistResponse:
        return SpecialistResponse(
            job_id=str(payload["job_id"]),
            node_role="risk",
            peer_id=peer_id,
            summary=(
                "The thesis fails if flow data weakens, liquidity deteriorates, "
                "or ETH loses support while volatility expands."
            ),
            scenario_view=ScenarioView(bull=0.25, base=0.35, bear=0.40),
            signals=[
                "counter_thesis: improving flows may already be priced in.",
                "invalidation: ETF flows turn negative for several sessions.",
                "invalidation: liquidity conditions tighten materially.",
                f"service: {service_name}",
            ],
            risks=[
                "risk: macro volatility can pressure high beta assets.",
                "risk: a support break would weaken the thesis setup.",
                "risk: single-thesis analysis should not be treated as advice.",
            ],
            confidence=0.68,
            citations=[],
            timestamp=_now(),
        )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
