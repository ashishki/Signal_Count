"""Event-query helpers for chain analyst snapshots."""

from __future__ import annotations

from app.nodes.chain_analyst.events import ChainEvent, ChainState

KNOWN_ROLES: tuple[str, ...] = ("regime", "narrative", "risk")


def contributions(state: ChainState) -> tuple[ChainEvent, ...]:
    return tuple(e for e in state.events if e.event_type == "ContributionRecorded")


def task_finalizations(state: ChainState) -> tuple[ChainEvent, ...]:
    return tuple(e for e in state.events if e.event_type == "TaskFinalized")


def reputation_records(state: ChainState) -> tuple[ChainEvent, ...]:
    return tuple(e for e in state.events if e.event_type == "ReputationRecorded")


def contributions_for_role(state: ChainState, role: str) -> tuple[ChainEvent, ...]:
    return tuple(e for e in contributions(state) if e.data.get("role") == role)


def latest_reputation_by_wallet(state: ChainState) -> dict[str, float]:
    snapshot: dict[str, float] = {}
    for event in reputation_records(state):
        wallet = str(event.data.get("wallet", "")).lower()
        if not wallet:
            continue
        try:
            score = float(event.data.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        snapshot[wallet] = score
    return snapshot


def distinct_finalized_jobs(state: ChainState) -> tuple[str, ...]:
    seen: list[str] = []
    seen_set: set[str] = set()
    for event in task_finalizations(state):
        job_id = str(event.data.get("job_id", ""))
        if job_id and job_id not in seen_set:
            seen.append(job_id)
            seen_set.add(job_id)
    return tuple(seen)
