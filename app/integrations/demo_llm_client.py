from __future__ import annotations

import json


class DemoLLMClient:
    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        content = "\n".join(message.get("content", "") for message in messages)
        if "risk specialist" in content:
            return json.dumps(
                {
                    "summary": "Risk case is elevated if flows weaken or support breaks.",
                    "counter_thesis": "ETF flow improvement may already be priced in.",
                    "risks": [
                        "ETF flows reverse for several sessions.",
                        "Liquidity tightens and volatility expands.",
                    ],
                    "invalidation_triggers": [
                        "ETH loses the recent support range.",
                        "ETF flow data fails to confirm the thesis.",
                    ],
                    "scenario_view": {"bull": 0.25, "base": 0.35, "bear": 0.40},
                    "confidence": 0.68,
                }
            )
        if "narrative specialist" in content:
            return json.dumps(
                {
                    "summary": (
                        "Narrative support is constructive but still depends on "
                        "confirmed flows and stable liquidity."
                    ),
                    "catalysts": [
                        "ETF flow improvement supports the upside case.",
                        "Stable liquidity keeps the base case intact.",
                    ],
                    "unknowns": ["Macro liquidity can shift quickly."],
                    "scenario_framing": [
                        "Bull case requires follow-through in flow data.",
                    ],
                    "scenario_view": {"bull": 0.42, "base": 0.38, "bear": 0.20},
                    "confidence": 0.62,
                }
            )
        return json.dumps(
            {
                "scenarios": {"bull": 0.39, "base": 0.38, "bear": 0.23},
                "supporting_evidence": [
                    "Regime and narrative specialists both identify constructive conditions.",
                ],
                "opposing_evidence": [
                    "Risk specialist flags flow reversal and support loss as failure paths.",
                ],
                "catalysts": [
                    "ETF flow improvement supports upside.",
                    "Liquidity remains stable.",
                ],
                "risks": [
                    "Macro volatility can pressure high beta assets.",
                    "The thesis weakens if flows reverse.",
                ],
                "invalidation_triggers": [
                    "ETH loses the recent support range.",
                    "ETF flow data fails to confirm the thesis.",
                ],
                "confidence_rationale": (
                    "Demo synthesis uses deterministic provider output; all specialist "
                    "roles responded with bounded confidence."
                ),
                "provenance": [],
                "partial": False,
                "partial_reason": None,
            }
        )
