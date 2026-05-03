"""Payout ledger schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PeerRoundEntry(BaseModel):
    peer_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    wallet: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")
    reputation_before: float = Field(ge=0.0, le=1.0)
    verifier_score: float = Field(ge=0.0, le=1.0)
    reputation_after: float = Field(ge=0.0, le=1.0)
    multiplier: float = Field(ge=0.0)
    base_wei: int = Field(ge=0)
    payout_wei: int = Field(ge=0)
    slashed: bool = False


class RoundLedger(BaseModel):
    round_index: int = Field(ge=0)
    job_id: str = Field(min_length=1)
    peers: list[PeerRoundEntry]
    total_payout_wei: int = Field(ge=0)


class SimulationLedger(BaseModel):
    schema_version: str = "signal-count.payout-loop/v1"
    base_wei: int = Field(ge=0)
    rounds: list[RoundLedger]
    final_reputation: dict[str, float]
    cumulative_payout_wei: dict[str, int]
