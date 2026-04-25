from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from os import getenv
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.observability.metrics import get_metrics
from app.observability.tracing import get_tracer


class LLMClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMClient:
    api_key: str | None = None
    base_url: str = "https://api.openai.com/v1/chat/completions"
    timeout_seconds: float = 30.0

    async def complete(self, model: str, messages: list[dict[str, str]]) -> str:
        tracer = get_tracer()
        metrics = get_metrics()
        counter = metrics.counter("llm_requests_total")
        histogram = metrics.histogram("llm_request_latency_ms")
        started_at = perf_counter()

        try:
            with tracer.span("llm.complete"):
                api_key = self.api_key or getenv("LLM_API_KEY")
                if not api_key:
                    raise LLMClientError("LLM_API_KEY is required")

                payload = {"model": model, "messages": messages}

                try:
                    response_body = await asyncio.to_thread(
                        self._post_json,
                        api_key,
                        payload,
                    )
                except (HTTPError, URLError, TimeoutError, ValueError) as exc:
                    raise LLMClientError("LLM provider request failed") from exc

                text = self._extract_text(response_body)
        except Exception:
            counter.add(1.0, operation="llm.complete", outcome="error")
            raise
        else:
            counter.add(1.0, operation="llm.complete", outcome="success")
            return text
        finally:
            histogram.record(
                _elapsed_ms(started_at),
                operation="llm.complete",
            )

    def _post_json(self, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    def _extract_text(self, response_body: dict[str, Any]) -> str:
        choices = response_body.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                text_segments = [
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                text = "".join(text_segments).strip()
                if text:
                    return text

        output_text = response_body.get("output_text")
        if isinstance(output_text, str) and output_text:
            return output_text

        raise ValueError("LLM provider response did not contain text content")


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)
