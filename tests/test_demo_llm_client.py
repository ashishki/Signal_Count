import asyncio
import json

from app.integrations.demo_llm_client import DemoLLMClient


def test_demo_llm_returns_narrative_payload() -> None:
    payload = asyncio.run(
        DemoLLMClient().complete(
            model="demo",
            messages=[{"role": "system", "content": "narrative specialist"}],
        )
    )

    assert json.loads(payload)["summary"].startswith("Narrative support")


def test_demo_llm_returns_final_memo_payload() -> None:
    payload = asyncio.run(
        DemoLLMClient().complete(
            model="demo",
            messages=[{"role": "system", "content": "final memo synthesizer"}],
        )
    )

    parsed = json.loads(payload)
    assert parsed["supporting_evidence"]
    assert parsed["opposing_evidence"]
    assert parsed["confidence_rationale"]
