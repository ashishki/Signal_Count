from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.schemas.contracts import ScenarioView, SpecialistResponse


@dataclass(frozen=True)
class RegimeSnapshot:
    price_return: float
    volatility: float


class RegimeService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._registry = AXLRegistry(self._settings)

    def analyze(self, job_id: str, snapshot: RegimeSnapshot) -> SpecialistResponse:
        scenario_view = self._build_scenario_view(snapshot)
        market_state = self._classify_market_state(snapshot)
        volatility_state = self._classify_volatility(snapshot.volatility)
        summary = (
            f"Price action is {market_state} with {volatility_state} volatility. "
            f"Base case remains the anchor while regime risk reflects the latest move."
        )
        signals = [
            f"price_return={snapshot.price_return:.2%}",
            f"volatility={snapshot.volatility:.2f}",
            f"market_state={market_state}",
            f"volatility_state={volatility_state}",
        ]
        risks = [
            "Trend can reverse quickly when realized volatility expands.",
            "Scenario weights are based on deterministic thresholds, not forward-looking news.",
        ]
        peer = self._registry.get_service_for_role("regime")
        confidence = max(
            0.0,
            min(
                1.0,
                0.5 + abs(snapshot.price_return) + max(0.0, 0.30 - snapshot.volatility),
            ),
        )

        return SpecialistResponse(
            job_id=job_id,
            node_role="regime",
            peer_id=peer.peer_id,
            summary=summary,
            scenario_view=scenario_view,
            signals=signals,
            risks=risks,
            confidence=confidence,
            citations=[],
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    def _build_scenario_view(self, snapshot: RegimeSnapshot) -> ScenarioView:
        trend_strength = max(min(snapshot.price_return / 0.10, 1.0), -1.0)
        volatility_pressure = max(min((snapshot.volatility - 0.20) / 0.20, 1.0), 0.0)

        bull_score = max(
            0.05, 1.0 + (0.7 * trend_strength) - (0.4 * volatility_pressure)
        )
        base_score = max(
            0.05, 1.2 - (0.2 * abs(trend_strength)) - (0.3 * volatility_pressure)
        )
        bear_score = max(
            0.05, 1.0 - (0.7 * trend_strength) + (0.5 * volatility_pressure)
        )

        total = bull_score + base_score + bear_score

        return ScenarioView(
            bull=bull_score / total,
            base=base_score / total,
            bear=bear_score / total,
        )

    def _classify_market_state(self, snapshot: RegimeSnapshot) -> str:
        if snapshot.price_return >= 0.05:
            return "risk-on"
        if snapshot.price_return <= -0.05:
            return "risk-off"
        return "range-bound"

    def _classify_volatility(self, volatility: float) -> str:
        if volatility >= 0.35:
            return "high"
        if volatility >= 0.20:
            return "moderate"
        return "contained"
