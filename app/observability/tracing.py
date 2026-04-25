from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class NoopSpan:
    name: str


class NoopTracer:
    @contextmanager
    def span(self, operation_name: str) -> Iterator[NoopSpan]:
        yield NoopSpan(name=operation_name)


def get_tracer() -> NoopTracer:
    return NoopTracer()
