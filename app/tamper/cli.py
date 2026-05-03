"""Write a tamper-evidence artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.tamper.harness import run_side_by_side


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tamper-demo",
        description=(
            "Run honest vs tampered side-by-side and write a single artifact "
            "for the proof console / demo recording."
        ),
    )
    parser.add_argument(
        "--out",
        default=".runtime/tamper/tamper-evidence.json",
        help="Output JSON path (will be created).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary on stdout.",
    )
    args = parser.parse_args(argv)

    artifact = run_side_by_side()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")

    if not args.quiet:
        _print_summary(artifact, out_path)

    if not artifact["summary"]["all_attacks_caught"]:
        return 1
    if artifact["honest"]["detection"]["status"] != "clean":
        return 2
    return 0


def _print_summary(artifact: dict, out_path: Path) -> None:
    summary = artifact["summary"]
    honest_status = artifact["honest"]["detection"]["status"]
    print(f"tamper-evidence written: {out_path}")
    print(f"  honest run:        {honest_status}")
    print(f"  attacks attempted: {summary['attack_count']}")
    print(f"  attacks caught:    {len(summary['attacks_caught'])}")
    if summary["attacks_missed"]:
        print(f"  attacks missed:    {summary['attacks_missed']}")
    for scenario in artifact["attacks"]:
        name = scenario["attack"]["name"]
        status = scenario["detection"]["status"]
        failed = ",".join(scenario["detection"]["failed_check_names"]) or "-"
        print(f"    [{status:>8}] {name}  (failed: {failed})")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
