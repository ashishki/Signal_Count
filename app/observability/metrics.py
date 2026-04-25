from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CounterEvent:
    name: str
    value: float
    labels: dict[str, str]


@dataclass(frozen=True)
class HistogramEvent:
    name: str
    value: float
    labels: dict[str, str]


@dataclass
class NoopCounter:
    name: str
    events: list[CounterEvent]

    def add(self, value: float = 1.0, **labels: str) -> None:
        self.events.append(
            CounterEvent(
                name=self.name,
                value=value,
                labels=dict(labels),
            )
        )


@dataclass
class NoopHistogram:
    name: str
    events: list[HistogramEvent]

    def record(self, value: float, **labels: str) -> None:
        self.events.append(
            HistogramEvent(
                name=self.name,
                value=value,
                labels=dict(labels),
            )
        )


@dataclass
class NoopMetrics:
    counter_events: list[CounterEvent] = field(default_factory=list)
    histogram_events: list[HistogramEvent] = field(default_factory=list)

    def counter(self, name: str) -> NoopCounter:
        return NoopCounter(name=name, events=self.counter_events)

    def histogram(self, name: str) -> NoopHistogram:
        return NoopHistogram(name=name, events=self.histogram_events)


_METRICS = NoopMetrics()


def get_metrics() -> NoopMetrics:
    return _METRICS
