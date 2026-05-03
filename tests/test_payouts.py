import json
from pathlib import Path

import pytest

from app.evaluation.payouts.cli import _round_from_dict
from app.evaluation.payouts.loop import simulate_rounds
from app.evaluation.payouts.policy import (
    BONUS_REPUTATION,
    FULL_PAYOUT_REPUTATION,
    MAX_MULTIPLIER,
    REPUTATION_ALPHA,
    SLASH_THRESHOLD,
    payout_multiplier,
    payout_wei,
    update_reputation,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "evaluation"
    / "payouts"
    / "fixtures"
    / "scenario.json"
)


def test_policy_updates_reputation_and_payouts() -> None:
    updated = update_reputation(current=0.7, verifier_score=0.85)

    assert updated == pytest.approx(REPUTATION_ALPHA * 0.85 + 0.7 * 0.7)
    assert payout_multiplier(SLASH_THRESHOLD - 0.01) == 0.0
    assert payout_multiplier(FULL_PAYOUT_REPUTATION) == pytest.approx(1.0)
    assert payout_multiplier(BONUS_REPUTATION) == pytest.approx(MAX_MULTIPLIER)
    assert payout_wei(reputation=FULL_PAYOUT_REPUTATION, base_wei=1_000_000_000) == (
        1_000_000_000
    )


def test_fixture_loop_shows_good_mediocre_bad_ordering() -> None:
    ledger = _ledger()

    good = _peer_entries(ledger, "peer-good")
    mediocre = _peer_entries(ledger, "peer-mediocre")
    bad = _peer_entries(ledger, "peer-bad")

    assert [e.payout_wei for e in good] == sorted(e.payout_wei for e in good)
    assert [e.payout_wei for e in mediocre] == sorted(
        (e.payout_wei for e in mediocre),
        reverse=True,
    )
    assert bad[-1].slashed is True
    assert bad[-1].payout_wei == 0
    assert (
        ledger.cumulative_payout_wei["peer-good"]
        > ledger.cumulative_payout_wei["peer-mediocre"]
        > ledger.cumulative_payout_wei["peer-bad"]
    )


def test_payout_ledger_round_trips_through_json() -> None:
    ledger = _ledger().model_dump(mode="json")

    assert json.loads(json.dumps(ledger, sort_keys=True)) == ledger
    assert ledger["schema_version"] == "signal-count.payout-loop/v1"


def _ledger():
    raw = json.loads(FIXTURE.read_text())
    rounds = [_round_from_dict(r) for r in raw["rounds"]]
    return simulate_rounds(
        rounds=rounds,
        base_wei=int(raw["base_wei"]),
        initial_reputation=dict(raw["initial_reputation"]),
    )


def _peer_entries(ledger, peer_id: str):
    return [
        entry
        for round_ledger in ledger.rounds
        for entry in round_ledger.peers
        if entry.peer_id == peer_id
    ]
