"""Narrative specialist service driven by structured LLM output."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.axl.registry import AXLRegistry
from app.config.settings import Settings
from app.integrations.llm_client import LLMClient
from app.schemas.contracts import ScenarioView, SpecialistResponse


class NarrativeService:
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
        headlines: list[str],
    ) -> SpecialistResponse:
        prompt = self._build_messages(headlines)
        llm_text = await self._llm_client.complete(model=self._model, messages=prompt)
        parsed = self._parse_response(llm_text)
        scenario_view = self._build_scenario_view(parsed)

        catalyst_signals = [f"catalyst: {item}" for item in parsed["catalysts"]]
        framing_signals = [
            f"scenario_frame: {item}" for item in parsed["scenario_framing"]
        ]
        unknown_risks = [f"unknown: {item}" for item in parsed["unknowns"]]

        registry_peer = self._registry.get_service_for_role("narrative")
        resolved_peer_id = peer_id or registry_peer.peer_id

        return SpecialistResponse(
            job_id=job_id,
            node_role="narrative",
            peer_id=resolved_peer_id,
            summary=parsed["summary"],
            scenario_view=scenario_view,
            signals=[*catalyst_signals, *framing_signals],
            risks=unknown_risks,
            confidence=self._coerce_confidence(parsed.get("confidence")),
            citations=headlines,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            agent_wallet=self._settings.node_wallet_address or None,
        )

    def _build_messages(self, headlines: list[str]) -> list[dict[str, str]]:
        headline_block = (
            "\n".join(f"- {headline}" for headline in headlines) or "- none"
        )
        return [
            {
                "role": "system",
                "content": (
                    "You are the narrative specialist for Signal Count. "
                    "Return compact JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize the narrative implied by these headlines. "
                    "Return JSON with keys: summary, catalysts, unknowns, "
                    "scenario_framing, scenario_view, confidence. "
                    "scenario_view must include bull, base, bear numeric weights.\n"
                    f"Headlines:\n{headline_block}"
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
                payload.get("summary"), fallback="Narrative context is mixed."
            ),
            "catalysts": self._coerce_list(payload.get("catalysts")),
            "unknowns": self._coerce_list(payload.get("unknowns")),
            "scenario_framing": self._coerce_list(payload.get("scenario_framing")),
            "scenario_view": payload.get("scenario_view", {}),
            "confidence": payload.get("confidence"),
        }

    def _build_scenario_view(self, parsed: dict[str, Any]) -> ScenarioView:
        raw_view = parsed["scenario_view"]
        bull = self._coerce_non_negative(raw_view.get("bull"), default=0.30)
        base = self._coerce_non_negative(raw_view.get("base"), default=0.40)
        bear = self._coerce_non_negative(raw_view.get("bear"), default=0.30)

        total = bull + base + bear
        if total == 0:
            bull, base, bear = 0.30, 0.40, 0.30
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
