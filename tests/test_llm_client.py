import asyncio
from urllib.error import URLError

from app.integrations.llm_client import LLMClient
from app.integrations import llm_client as llm_client_module
from app.observability.metrics import NoopMetrics
from app.observability.tracing import get_tracer


def test_get_tracer_returns_object() -> None:
    tracer = get_tracer()

    assert tracer is not None


def test_llm_client_complete_executes_with_stub_response() -> None:
    metrics = NoopMetrics()

    class StubLLMClient(LLMClient):
        def _post_json(
            self, api_key: str, payload: dict[str, object]
        ) -> dict[str, object]:
            return {"choices": [{"message": {"content": "stubbed response"}}]}

    client = StubLLMClient(api_key="test-key")
    original_get_metrics = llm_client_module.get_metrics
    llm_client_module.get_metrics = lambda: metrics

    try:
        result = asyncio.run(
            client.complete(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hello"}],
            )
        )
    finally:
        llm_client_module.get_metrics = original_get_metrics

    assert result == "stubbed response"
    assert metrics.counter_events[0].labels["outcome"] == "success"
    assert metrics.histogram_events[0].name == "llm_request_latency_ms"


def test_llm_client_complete_records_error_metrics() -> None:
    metrics = NoopMetrics()

    class ErroringLLMClient(LLMClient):
        def _post_json(
            self, api_key: str, payload: dict[str, object]
        ) -> dict[str, object]:
            raise URLError("network down")

    client = ErroringLLMClient(api_key="test-key")
    original_get_metrics = llm_client_module.get_metrics
    llm_client_module.get_metrics = lambda: metrics

    try:
        try:
            asyncio.run(
                client.complete(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": "hello"}],
                )
            )
        except RuntimeError as exc:
            assert str(exc) == "LLM provider request failed"
        else:
            raise AssertionError("Expected LLM provider failure")
    finally:
        llm_client_module.get_metrics = original_get_metrics

    assert metrics.counter_events[0].labels["outcome"] == "error"
    assert metrics.histogram_events[0].name == "llm_request_latency_ms"
