from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.integrations.llm_client import LLMClient
from app.schemas.contracts import ScenarioView, SpecialistResponse


class RiskService:
    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._llm_client = llm_client
        self._settings = settings or Settings()
        self._registry = AXLRegistry(self._settings)
        self._model = model

    async def analyze(
        self,
        job_id: str,
        peer_id: str,
        thesis: str,
    ) -> SpecialistResponse:
        prompt = self._build_messages(thesis)
        llm_text = await self._llm_client.complete(model=self._model, messages=prompt)
        parsed = self._parse_response(llm_text)
        scenario_view = self._build_scenario_view(parsed)

        registry_peer = self._registry.get_service_for_role("risk")
        resolved_peer_id = peer_id or registry_peer.peer_id
        signals = [f"counter_thesis: {parsed.get('counter_thesis', '')}"]
        signals.extend(
            f"invalidation: {item}" for item in parsed["invalidation_triggers"]
        )
        risks = [f"risk: {item}" for item in parsed["risks"]]

        return SpecialistResponse(
            job_id=job_id,
            node_role="risk",
            peer_id=resolved_peer_id,
            summary=parsed["summary"],
            scenario_view=scenario_view,
            signals=signals,
            risks=risks,
            confidence=self._coerce_confidence(parsed.get("confidence")),
            citations=[],
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )

    def _build_messages(self, thesis: str) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the risk specialist for Signal Count. "
                    "Return compact JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate the strongest opposing case for this thesis. "
                    "Return JSON with keys: summary, counter_thesis, risks, "
                    "invalidation_triggers, scenario_view, confidence. "
                    "scenario_view must include bull, base, bear numeric weights.\n"
                    f"Thesis:\n{thesis}"
                ),
            },
        ]

    def _parse_response(self, llm_text: str) -> dict[str, Any]:
        json_text = llm_text.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response is not valid JSON") from exc

        return {
            "summary": self._coerce_text(
                payload.get("summary"),
                fallback="Risk conditions remain unresolved.",
            ),
            "counter_thesis": self._coerce_text(
                payload.get("counter_thesis"),
                fallback="The thesis can fail if the expected catalyst does not arrive.",
            ),
            "risks": self._coerce_list(payload.get("risks")),
            "invalidation_triggers": self._coerce_list(
                payload.get("invalidation_triggers")
            ),
            "scenario_view": payload.get("scenario_view", {}),
            "confidence": payload.get("confidence"),
        }

    def _build_scenario_view(self, parsed: dict[str, Any]) -> ScenarioView:
        raw_view = parsed["scenario_view"]
        bull = self._coerce_non_negative(raw_view.get("bull"), default=0.25)
        base = self._coerce_non_negative(raw_view.get("base"), default=0.35)
        bear = self._coerce_non_negative(raw_view.get("bear"), default=0.40)

        total = bull + base + bear
        if total == 0:
            bull, base, bear = 0.25, 0.35, 0.40
            total = 1.0

        return ScenarioView(bull=bull / total, base=base / total, bear=bear / total)

    def _coerce_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            item.strip() for item in value if isinstance(item, str) and item.strip()
        ]

    def _coerce_text(self, value: Any, fallback: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return fallback

    def _coerce_non_negative(self, value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, number)

    def _coerce_confidence(self, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.5
        return min(1.0, max(0.0, number))
