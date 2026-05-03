"""Write a deterministic chain-analyst response artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.identity.hashing import canonical_json_hash
from app.nodes.chain_analyst.rpc import FixtureRPC
from app.nodes.chain_analyst.service import analyze
from app.schemas.contracts import TaskSpec

DEFAULT_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chain_state.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chain-analyst",
        description=(
            "Run the deterministic on-chain analyst against a fixture or "
            "live RPC and write the SpecialistResponse + output_hash."
        ),
    )
    parser.add_argument(
        "--fixture",
        default=str(DEFAULT_FIXTURE),
        help="Path to a chain-state JSON snapshot (fixture mode).",
    )
    parser.add_argument(
        "--block",
        type=int,
        default=None,
        help="Pin to a specific block number; default is the snapshot's latest block.",
    )
    parser.add_argument(
        "--job-id",
        default="demo-job-chain-analyst-001",
    )
    parser.add_argument(
        "--asset",
        default="ETH",
    )
    parser.add_argument(
        "--thesis",
        default=(
            "On-chain swarm coverage at this block is sufficient to support "
            "a follow-on dispatch."
        ),
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--out",
        default=".runtime/chain-analyst/chain-analyst-response.json",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    rpc = FixtureRPC(args.fixture)
    task = TaskSpec(
        job_id=args.job_id,
        thesis=args.thesis,
        asset=args.asset,
        horizon_days=args.horizon_days,
    )
    response = analyze(rpc=rpc, task=task, block_number=args.block)
    output_hash = canonical_json_hash(response)

    artifact = {
        "schema": "signal-count.chain-analyst-response/v1",
        "task": task.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "output_hash": output_hash,
        "block_number": args.block,
        "fixture": str(Path(args.fixture).resolve()),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")

    if not args.quiet:
        _print_summary(artifact, out_path)
    return 0


def _print_summary(artifact: dict, out_path: Path) -> None:
    response = artifact["response"]
    print(f"chain-analyst response written: {out_path}")
    print(f"  output_hash:       {artifact['output_hash']}")
    print(
        f"  block_number:      {response['ree_receipt_body']['metrics']['block_number']}"
    )
    print(
        f"  block_timestamp:   {response['ree_receipt_body']['metrics']['block_timestamp']}"
    )
    print(f"  receipt_status:    {response['receipt_status']}")
    print(f"  confidence:        {response['confidence']}")
    print(
        f"  finalized_tasks:   {response['ree_receipt_body']['metrics']['finalized_task_count']}"
    )
    print(
        f"  contributions:     {response['ree_receipt_body']['metrics']['contribution_count']}"
    )
    print()
    print("  signals:")
    for signal in response["signals"]:
        print(f"    - {signal}")
    print("  risks:")
    for risk in response["risks"]:
        print(f"    - {risk}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
