"""Local projections rebuilt from indexed chain events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.indexer.chain_events import IndexedChainEvent

SCORE_SCALE = 1_000_000


@dataclass(frozen=True)
class TaskProjection:
    task_id: int
    task_hash: str
    metadata_uri: str
    finalized: bool = False
    memo_hash: str | None = None
    source: str = "indexed_chain"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "task_hash": self.task_hash,
            "metadata_uri": self.metadata_uri,
            "finalized": self.finalized,
            "memo_hash": self.memo_hash,
            "source": self.source,
        }


@dataclass(frozen=True)
class ContributionProjection:
    task_id: int
    agent: str
    role: str
    output_hash: str
    ree_receipt_hash: str
    metadata_uri: str
    transaction_hash: str
    source: str = "indexed_chain"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "role": self.role,
            "output_hash": self.output_hash,
            "ree_receipt_hash": self.ree_receipt_hash,
            "metadata_uri": self.metadata_uri,
            "transaction_hash": self.transaction_hash,
            "source": self.source,
        }


@dataclass(frozen=True)
class VerificationProjection:
    task_id: int
    verifier: str
    verdict_hash: str
    score: float
    transaction_hash: str
    source: str = "indexed_chain"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "verifier": self.verifier,
            "verdict_hash": self.verdict_hash,
            "score": self.score,
            "transaction_hash": self.transaction_hash,
            "source": self.source,
        }


@dataclass(frozen=True)
class ReputationProjection:
    task_id: int
    agent: str
    role: str
    score: float
    points: float
    native_test_payout_wei: int
    metadata_uri: str
    transaction_hash: str
    source: str = "indexed_chain"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "agent": self.agent,
            "role": self.role,
            "score": self.score,
            "points": self.points,
            "native_test_payout_wei": self.native_test_payout_wei,
            "metadata_uri": self.metadata_uri,
            "transaction_hash": self.transaction_hash,
            "source": self.source,
        }


@dataclass(frozen=True)
class AgentReputationEntry:
    agent_wallet: str
    node_role: str
    reputation_points: float
    recorded_contributions: int
    total_verifier_score: float
    native_test_payout_wei: int

    def to_dict(self) -> dict[str, object]:
        return {
            "agent_wallet": self.agent_wallet,
            "node_role": self.node_role,
            "reputation_points": self.reputation_points,
            "recorded_contributions": self.recorded_contributions,
            "total_verifier_score": self.total_verifier_score,
            "native_test_payout_wei": self.native_test_payout_wei,
            "source": "indexed_chain",
        }


@dataclass(frozen=True)
class ChainEventsProjection:
    tasks: dict[int, TaskProjection] = field(default_factory=dict)
    contributions: list[ContributionProjection] = field(default_factory=list)
    verifications: list[VerificationProjection] = field(default_factory=list)
    reputations: list[ReputationProjection] = field(default_factory=list)

    @property
    def agent_leaderboard(self) -> list[AgentReputationEntry]:
        aggregates: dict[tuple[str, str], dict[str, float | int | str]] = {}
        for record in self.reputations:
            key = (record.agent, record.role)
            aggregate = aggregates.setdefault(
                key,
                {
                    "agent_wallet": record.agent,
                    "node_role": record.role,
                    "reputation_points": 0.0,
                    "recorded_contributions": 0,
                    "total_verifier_score": 0.0,
                    "native_test_payout_wei": 0,
                },
            )
            aggregate["reputation_points"] = round(
                float(aggregate["reputation_points"]) + record.points,
                6,
            )
            aggregate["recorded_contributions"] = (
                int(aggregate["recorded_contributions"]) + 1
            )
            aggregate["total_verifier_score"] = round(
                float(aggregate["total_verifier_score"]) + record.score,
                6,
            )
            aggregate["native_test_payout_wei"] = (
                int(aggregate["native_test_payout_wei"]) + record.native_test_payout_wei
            )

        return sorted(
            (
                AgentReputationEntry(
                    agent_wallet=str(aggregate["agent_wallet"]),
                    node_role=str(aggregate["node_role"]),
                    reputation_points=float(aggregate["reputation_points"]),
                    recorded_contributions=int(aggregate["recorded_contributions"]),
                    total_verifier_score=float(aggregate["total_verifier_score"]),
                    native_test_payout_wei=int(aggregate["native_test_payout_wei"]),
                )
                for aggregate in aggregates.values()
            ),
            key=lambda entry: (
                -entry.reputation_points,
                entry.node_role,
                entry.agent_wallet,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "contributions": [
                contribution.to_dict() for contribution in self.contributions
            ],
            "verifications": [
                verification.to_dict() for verification in self.verifications
            ],
            "reputations": [reputation.to_dict() for reputation in self.reputations],
            "agent_leaderboard": [entry.to_dict() for entry in self.agent_leaderboard],
        }


def build_chain_events_projection(
    events: Iterable[IndexedChainEvent],
) -> ChainEventsProjection:
    tasks: dict[int, TaskProjection] = {}
    contributions: list[ContributionProjection] = []
    verifications: list[VerificationProjection] = []
    reputations: list[ReputationProjection] = []

    for event in sorted(events, key=lambda item: (item.block_number, item.log_index)):
        args = event.args
        if event.event_name == "TaskCreated":
            task_id = int(args["task_id"])
            tasks[task_id] = TaskProjection(
                task_id=task_id,
                task_hash=str(args["task_hash"]),
                metadata_uri=str(args["metadata_uri"]),
                finalized=tasks.get(task_id, TaskProjection(task_id, "", "")).finalized,
                memo_hash=tasks.get(task_id, TaskProjection(task_id, "", "")).memo_hash,
            )
        elif event.event_name == "TaskFinalized":
            task_id = int(args["task_id"])
            existing = tasks.get(task_id)
            tasks[task_id] = TaskProjection(
                task_id=task_id,
                task_hash=existing.task_hash if existing else "",
                metadata_uri=existing.metadata_uri if existing else "",
                finalized=True,
                memo_hash=str(args["memo_hash"]),
            )
        elif event.event_name == "ContributionRecorded":
            contributions.append(
                ContributionProjection(
                    task_id=int(args["task_id"]),
                    agent=str(args["agent"]),
                    role=str(args["role"]),
                    output_hash=str(args["output_hash"]),
                    ree_receipt_hash=str(args["ree_receipt_hash"]),
                    metadata_uri=str(args["metadata_uri"]),
                    transaction_hash=event.transaction_hash,
                )
            )
        elif event.event_name == "VerificationRecorded":
            verifications.append(
                VerificationProjection(
                    task_id=int(args["task_id"]),
                    verifier=str(args["verifier"]),
                    verdict_hash=str(args["verdict_hash"]),
                    score=_unscale(args["score"]),
                    transaction_hash=event.transaction_hash,
                )
            )
        elif event.event_name == "ReputationRecorded":
            reputations.append(
                ReputationProjection(
                    task_id=int(args["task_id"]),
                    agent=str(args["agent"]),
                    role=str(args["role"]),
                    score=_unscale(args["score"]),
                    points=_unscale(args["points"]),
                    native_test_payout_wei=int(args["native_test_payout_wei"]),
                    metadata_uri=str(args["metadata_uri"]),
                    transaction_hash=event.transaction_hash,
                )
            )

    return ChainEventsProjection(
        tasks=dict(sorted(tasks.items())),
        contributions=contributions,
        verifications=verifications,
        reputations=reputations,
    )


def _unscale(value: object) -> float:
    return round(int(value) / SCORE_SCALE, 6)
