"""Shared noop tracing primitives for external-call instrumentation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class NoopSpan:
    """Minimal span object compatible with context-manager usage."""

    name: str


class NoopTracer:
    """Tracer that yields inert spans without external dependencies."""

    @contextmanager
    def span(self, operation_name: str) -> Iterator[NoopSpan]:
        yield NoopSpan(name=operation_name)


def get_tracer() -> NoopTracer:
    """Return the shared noop tracer implementation."""

    return NoopTracer()
