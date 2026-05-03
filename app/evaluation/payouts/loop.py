"""Round-by-round reputation payout simulation."""

from __future__ import annotations

from dataclasses import dataclass

from app.evaluation.payouts.policy import (
    INITIAL_REPUTATION,
    SLASH_THRESHOLD,
    payout_multiplier,
    payout_wei,
    update_reputation,
)
from app.evaluation.payouts.schemas import (
    PeerRoundEntry,
    RoundLedger,
    SimulationLedger,
)


@dataclass(frozen=True)
class PeerScore:
    peer_id: str
    role: str
    wallet: str
    verifier_score: float


@dataclass(frozen=True)
class RoundInput:
    round_index: int
    job_id: str
    peer_scores: tuple[PeerScore, ...]


def run_round(
    *,
    round_input: RoundInput,
    reputation_state: dict[str, float],
    base_wei: int,
) -> tuple[RoundLedger, dict[str, float]]:
    entries: list[PeerRoundEntry] = []
    next_state = dict(reputation_state)

    for score in round_input.peer_scores:
        before = next_state.get(score.peer_id, INITIAL_REPUTATION)
        after = update_reputation(
            current=before,
            verifier_score=score.verifier_score,
        )
        multiplier = payout_multiplier(after)
        payout = payout_wei(reputation=after, base_wei=base_wei)
        entries.append(
            PeerRoundEntry(
                peer_id=score.peer_id,
                role=score.role,
                wallet=score.wallet,
                reputation_before=round(before, 6),
                verifier_score=round(score.verifier_score, 6),
                reputation_after=after,
                multiplier=round(multiplier, 6),
                base_wei=base_wei,
                payout_wei=payout,
                slashed=after < SLASH_THRESHOLD,
            )
        )
        next_state[score.peer_id] = after

    ledger = RoundLedger(
        round_index=round_input.round_index,
        job_id=round_input.job_id,
        peers=entries,
        total_payout_wei=sum(e.payout_wei for e in entries),
    )
    return ledger, next_state


def simulate_rounds(
    *,
    rounds: list[RoundInput],
    base_wei: int,
    initial_reputation: dict[str, float] | None = None,
) -> SimulationLedger:
    state: dict[str, float] = dict(initial_reputation or {})
    round_ledgers: list[RoundLedger] = []
    cumulative: dict[str, int] = {}

    for round_input in rounds:
        ledger, state = run_round(
            round_input=round_input,
            reputation_state=state,
            base_wei=base_wei,
        )
        round_ledgers.append(ledger)
        for entry in ledger.peers:
            cumulative[entry.peer_id] = (
                cumulative.get(entry.peer_id, 0) + entry.payout_wei
            )

    return SimulationLedger(
        base_wei=base_wei,
        rounds=round_ledgers,
        final_reputation={k: round(v, 6) for k, v in state.items()},
        cumulative_payout_wei=cumulative,
    )
