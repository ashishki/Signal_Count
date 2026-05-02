"""Structured provenance helpers for completed jobs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NodeExecutionRecord:
    """Execution metadata for one specialist call."""

    node_role: str
    peer_id: str
    status: str
    latency_ms: float
    service_name: str = ""
    transport: str = ""
    dispatch_target: str = ""
    selection_reason: str = ""
    attempted_peer_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "node_role": self.node_role,
            "peer_id": self.peer_id,
            "status": self.status,
            "latency_ms": self.latency_ms,
        }
        if self.service_name:
            payload["service_name"] = self.service_name
        if self.transport:
            payload["transport"] = self.transport
        if self.dispatch_target:
            payload["dispatch_target"] = self.dispatch_target
        if self.selection_reason:
            payload["selection_reason"] = self.selection_reason
        if self.attempted_peer_ids:
            payload["attempted_peer_ids"] = list(self.attempted_peer_ids)
        return payload
