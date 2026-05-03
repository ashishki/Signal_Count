"""Pre-decoded chain event types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EventType = Literal[
    "ContributionRecorded",
    "TaskFinalized",
    "ReputationRecorded",
]


@dataclass(frozen=True)
class ChainEvent:
    event_type: EventType
    block_number: int
    log_index: int
    transaction_hash: str
    data: dict[str, Any]

    @property
    def idempotency_key(self) -> str:
        return f"{self.transaction_hash}:{self.log_index}"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ChainEvent:
        return cls(
            event_type=raw["event_type"],
            block_number=int(raw["block_number"]),
            log_index=int(raw["log_index"]),
            transaction_hash=str(raw["transaction_hash"]),
            data=dict(raw["data"]),
        )


@dataclass(frozen=True)
class ChainState:
    block_number: int
    block_timestamp: int
    chain_id: int
    contract_addresses: dict[str, str]
    events: tuple[ChainEvent, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ChainState:
        return cls(
            block_number=int(raw["block_number"]),
            block_timestamp=int(raw["block_timestamp"]),
            chain_id=int(raw["chain_id"]),
            contract_addresses=dict(raw["contract_addresses"]),
            events=tuple(ChainEvent.from_dict(e) for e in raw.get("events", [])),
        )
