from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    signal_count_offline_demo: bool = (
        getenv("SIGNAL_COUNT_OFFLINE_DEMO", "")
    ).lower() in {"1", "true", "yes"}
    signal_count_demo_llm: bool = (getenv("SIGNAL_COUNT_DEMO_LLM", "")).lower() in {
        "1",
        "true",
        "yes",
    }
    signal_count_offline_fail_role: str = getenv("SIGNAL_COUNT_OFFLINE_FAIL_ROLE", "")
    axl_local_base_url: str = getenv("AXL_LOCAL_BASE_URL", "http://127.0.0.1:9002")
    axl_topology_path: str = getenv("AXL_TOPOLOGY_PATH", "/topology")
    regime_peer_id: str = getenv("REGIME_PEER_ID", "peer-regime-example")
    regime_service_name: str = getenv("REGIME_SERVICE_NAME", "regime_analyst")
    narrative_peer_id: str = getenv("NARRATIVE_PEER_ID", "peer-narrative-example")
    narrative_service_name: str = getenv(
        "NARRATIVE_SERVICE_NAME",
        "narrative_analyst",
    )
    risk_peer_id: str = getenv("RISK_PEER_ID", "peer-risk-example")
    risk_service_name: str = getenv("RISK_SERVICE_NAME", "risk_analyst")
    axl_mcp_router_url: str = getenv("AXL_MCP_ROUTER_URL", "http://127.0.0.1:9003")
    node_role: str = getenv("NODE_ROLE", "regime")
    node_service_name: str = getenv("NODE_SERVICE_NAME", "")
    node_public_url: str = getenv("NODE_PUBLIC_URL", "http://127.0.0.1:7101")


def get_settings() -> Settings:
    return Settings()
