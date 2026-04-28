"""Role to peer/service mapping for AXL specialist nodes."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings


@dataclass(frozen=True)
class PeerService:
    peer_id: str
    service_name: str


class AXLRegistry:
    def __init__(self, settings: Settings) -> None:
        self._services = {
            "regime": PeerService(
                peer_id=settings.regime_peer_id,
                service_name=settings.regime_service_name,
            ),
            "narrative": PeerService(
                peer_id=settings.narrative_peer_id,
                service_name=settings.narrative_service_name,
            ),
            "risk": PeerService(
                peer_id=settings.risk_peer_id,
                service_name=settings.risk_service_name,
            ),
        }

    def get_service_for_role(self, role: str) -> PeerService:
        service = self._services.get(role)
        if service is None:
            raise ValueError(f"AXLRegistry: unknown role '{role}'")
        return service
