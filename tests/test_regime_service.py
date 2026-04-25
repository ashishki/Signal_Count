from app.config.settings import Settings
from app.nodes.regime.service import RegimeService, RegimeSnapshot
from app.schemas.contracts import SpecialistResponse


def test_regime_service_returns_valid_specialist_response() -> None:
    service = RegimeService(Settings())

    response = service.analyze(
        job_id="job-regime-123",
        snapshot=RegimeSnapshot(price_return=0.08, volatility=0.18),
    )

    assert isinstance(response, SpecialistResponse)
    assert response.job_id == "job-regime-123"
    assert response.node_role == "regime"
    assert response.peer_id == "peer-regime-example"
    assert response.summary
    assert "price_return=8.00%" in response.signals
    assert response.confidence > 0.0


def test_regime_service_scenario_distribution_is_normalized() -> None:
    service = RegimeService(Settings())

    response = service.analyze(
        job_id="job-regime-456",
        snapshot=RegimeSnapshot(price_return=-0.04, volatility=0.33),
    )

    total = (
        response.scenario_view.bull
        + response.scenario_view.base
        + response.scenario_view.bear
    )

    assert total == 1.0
