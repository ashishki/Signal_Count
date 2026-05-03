"""Metric computations for chain analyst snapshots."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from app.nodes.chain_analyst.events import ChainState
from app.nodes.chain_analyst.queries import (
    KNOWN_ROLES,
    contributions_for_role,
    distinct_finalized_jobs,
    latest_reputation_by_wallet,
)


@dataclass(frozen=True)
class PeerMetric:
    peer_id: str
    wallet: str
    contributions: int
    last_block: int
    reputation: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoleMetric:
    role: str
    peer_count: int
    contribution_count: int
    avg_reputation: float
    top_peer: PeerMetric | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "peer_count": self.peer_count,
            "contribution_count": self.contribution_count,
            "avg_reputation": self.avg_reputation,
            "top_peer": self.top_peer.to_dict() if self.top_peer else None,
        }


@dataclass(frozen=True)
class ChainMetrics:
    block_number: int
    block_timestamp: int
    chain_id: int
    finalized_task_count: int
    contribution_count: int
    distinct_wallets: int
    roles: tuple[RoleMetric, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_number": self.block_number,
            "block_timestamp": self.block_timestamp,
            "chain_id": self.chain_id,
            "finalized_task_count": self.finalized_task_count,
            "contribution_count": self.contribution_count,
            "distinct_wallets": self.distinct_wallets,
            "roles": [r.to_dict() for r in self.roles],
        }


def compute_metrics(state: ChainState) -> ChainMetrics:
    reputation = latest_reputation_by_wallet(state)
    role_metrics = tuple(
        _compute_role_metric(state, role, reputation) for role in KNOWN_ROLES
    )

    contribution_total = sum(r.contribution_count for r in role_metrics)
    distinct_wallets = len(_distinct_wallets(state))

    return ChainMetrics(
        block_number=state.block_number,
        block_timestamp=state.block_timestamp,
        chain_id=state.chain_id,
        finalized_task_count=len(distinct_finalized_jobs(state)),
        contribution_count=contribution_total,
        distinct_wallets=distinct_wallets,
        roles=role_metrics,
    )


def _compute_role_metric(
    state: ChainState, role: str, reputation: dict[str, float]
) -> RoleMetric:
    role_events = contributions_for_role(state, role)
    by_peer: dict[str, list] = {}
    for event in role_events:
        peer_id = str(event.data.get("peer_id", ""))
        if not peer_id:
            continue
        by_peer.setdefault(peer_id, []).append(event)

    peers: list[PeerMetric] = []
    for peer_id in sorted(by_peer):
        events = by_peer[peer_id]
        wallet = _representative_wallet(events)
        last_block = max(e.block_number for e in events)
        rep = reputation.get(wallet.lower(), 0.0) if wallet else 0.0
        peers.append(
            PeerMetric(
                peer_id=peer_id,
                wallet=wallet,
                contributions=len(events),
                last_block=last_block,
                reputation=round(rep, 6),
            )
        )

    avg_reputation = (
        round(sum(p.reputation for p in peers) / len(peers), 6) if peers else 0.0
    )

    top_peer = _top_peer(peers)

    return RoleMetric(
        role=role,
        peer_count=len(peers),
        contribution_count=len(role_events),
        avg_reputation=avg_reputation,
        top_peer=top_peer,
    )


def _representative_wallet(events) -> str:
    chosen = max(events, key=lambda e: (e.block_number, e.log_index))
    return str(chosen.data.get("wallet", ""))


def _top_peer(peers: list[PeerMetric]) -> PeerMetric | None:
    if not peers:
        return None
    return max(
        peers,
        key=lambda p: (p.reputation, p.contributions, _peer_id_sort_key(p.peer_id)),
    )


def _peer_id_sort_key(peer_id: str) -> tuple:
    return tuple(-ord(c) for c in peer_id)


def _distinct_wallets(state: ChainState) -> set[str]:
    wallets: set[str] = set()
    for event in state.events:
        wallet = str(event.data.get("wallet", "")).lower()
        if wallet:
            wallets.add(wallet)
    return wallets


def confidence_from_metrics(metrics: ChainMetrics) -> float:
    evidence = metrics.contribution_count + metrics.finalized_task_count
    raw = 0.4 + 0.06 * math.log1p(evidence)
    return round(min(raw, 0.9), 4)
