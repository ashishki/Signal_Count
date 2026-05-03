"""Write a reputation-payout ledger artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.evaluation.payouts.loop import (
    PeerScore,
    RoundInput,
    simulate_rounds,
)
from app.evaluation.payouts.schemas import RoundLedger, SimulationLedger

DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "scenario.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reputation-payouts",
        description=(
            "Simulate the reputation-weighted payout loop over a scenario "
            "and write a per-round ledger plus cumulative totals."
        ),
    )
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--out",
        default=".runtime/payout-loop/payout-ledger.json",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    scenario = json.loads(Path(args.fixture).read_text())
    rounds = [_round_from_dict(r) for r in scenario["rounds"]]

    ledger = simulate_rounds(
        rounds=rounds,
        base_wei=int(scenario["base_wei"]),
        initial_reputation=dict(scenario.get("initial_reputation", {})),
    )

    artifact = ledger.model_dump(mode="json")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")

    if not args.quiet:
        _print_table(ledger, out_path)
    return 0


def _round_from_dict(raw: dict) -> RoundInput:
    return RoundInput(
        round_index=int(raw["round_index"]),
        job_id=str(raw["job_id"]),
        peer_scores=tuple(
            PeerScore(
                peer_id=str(p["peer_id"]),
                role=str(p["role"]),
                wallet=str(p["wallet"]),
                verifier_score=float(p["verifier_score"]),
            )
            for p in raw["peer_scores"]
        ),
    )


def _print_table(ledger: SimulationLedger, out_path: Path) -> None:
    print(f"payout-ledger written: {out_path}")
    print(f"  base_wei: {ledger.base_wei}")
    print()
    header = (
        f"{'round':>5}  {'peer':<14}  {'role':<10}  "
        f"{'rep_before':>10}  {'score':>6}  {'rep_after':>10}  "
        f"{'mult':>6}  {'payout_wei':>12}  {'slashed':>7}"
    )
    print(header)
    print("-" * len(header))
    for round_ledger in ledger.rounds:
        for entry in round_ledger.peers:
            print(
                f"{round_ledger.round_index:>5}  "
                f"{entry.peer_id:<14}  "
                f"{entry.role:<10}  "
                f"{entry.reputation_before:>10.4f}  "
                f"{entry.verifier_score:>6.2f}  "
                f"{entry.reputation_after:>10.4f}  "
                f"{entry.multiplier:>6.4f}  "
                f"{entry.payout_wei:>12}  "
                f"{'YES' if entry.slashed else 'no':>7}"
            )
        print()

    print("cumulative payouts:")
    for peer_id, total in sorted(ledger.cumulative_payout_wei.items()):
        final_rep = ledger.final_reputation.get(peer_id, 0.0)
        print(
            f"  {peer_id:<14}  cumulative_wei={total:>12}  "
            f"final_reputation={final_rep:.4f}"
        )


def _round_ledger_index(rl: RoundLedger) -> int:
    return rl.round_index


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
