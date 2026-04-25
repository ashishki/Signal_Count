import pytest

from app.axl.client import AXLClient
from app.axl.registry import AXLRegistry
from app.config.settings import Settings


def test_registry_returns_peer_and_service_for_known_roles() -> None:
    settings = Settings()
    registry = AXLRegistry(settings)

    regime = registry.get_service_for_role("regime")
    narrative = registry.get_service_for_role("narrative")
    risk = registry.get_service_for_role("risk")

    assert regime.peer_id == "peer-regime-example"
    assert regime.service_name == "regime_analyst"
    assert narrative.peer_id == "peer-narrative-example"
    assert narrative.service_name == "narrative_analyst"
    assert risk.peer_id == "peer-risk-example"
    assert risk.service_name == "risk_analyst"


def test_axl_client_targets_local_bridge_mcp_path() -> None:
    settings = Settings()
    registry = AXLRegistry(settings)
    client = AXLClient(settings, registry)

    assert (
        client.build_mcp_request_path("risk")
        == "http://127.0.0.1:9002/mcp/peer-risk-example/risk_analyst"
    )
    assert client.build_mcp_request_path("regime").startswith("http://127.0.0.1:9002")


def test_axl_client_fetches_topology_from_local_bridge() -> None:
    settings = Settings()
    registry = AXLRegistry(settings)
    client = AXLClient(settings, registry)

    assert client.build_topology_path() == "http://127.0.0.1:9002/topology"


def test_registry_raises_value_error_for_unknown_role() -> None:
    settings = Settings()
    registry = AXLRegistry(settings)

    with pytest.raises(ValueError, match="unknown role 'coordinator'"):
        registry.get_service_for_role("coordinator")
