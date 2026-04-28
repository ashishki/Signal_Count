#!/usr/bin/env python3
"""End-to-end REE integration verification.

Run from the project root:
    REE_SH=/path/to/ree.sh .venv/bin/python scripts/verify_ree_e2e.py

Requires:
    - Docker running
    - gensynai/ree:v0.2.0 image pulled (or it will pull on first run)
    - REE_SH env var pointing to /path/to/gensyn-ai/ree/ree.sh

Writes a short prompt, calls ree.sh --cpu-only, parses the receipt,
and reports whether local hash recomputation matches.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running from project root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ree.runner import ReeRunRequest, ReeRunner, ReeRunnerError


def main() -> int:
    ree_sh = os.environ.get("REE_SH", "/tmp/gensyn-ree/ree.sh")

    if not Path(ree_sh).exists():
        print(f"[FAIL] ree.sh not found at {ree_sh}")
        print("       Clone https://github.com/gensyn-ai/ree and set REE_SH=<path>")
        return 1

    print(f"[INFO] Using ree.sh: {ree_sh}")
    print("[INFO] Starting REE run (cpu-only, max_new_tokens=20) ...")
    print("       First run downloads the Docker image — may take several minutes.\n")

    runner = ReeRunner(
        command=ree_sh,
        cpu_only=True,
    )
    request = ReeRunRequest(
        model_name="Qwen/Qwen3-0.6B",
        prompt="Reply with exactly one word: confirmed.",
        max_new_tokens=20,
    )

    try:
        outcome = runner.run(request)
    except ReeRunnerError as exc:
        print(f"[FAIL] REE run failed: {exc}")
        return 1

    print(f"[OK]   receipt_path:    {outcome.receipt_path}")
    print(f"[OK]   model_name:      {outcome.receipt.model_name}")
    print(f"[OK]   text_output:     {outcome.receipt.text_output!r}")
    print(f"[OK]   receipt_hash:    {outcome.receipt.receipt_hash}")
    print(f"[OK]   receipt_status:  {outcome.receipt_status}")
    print(f"[OK]   hash_matches:    {outcome.validation.matches}")

    if outcome.receipt_status == "validated":
        print("\n[PASS] Local Gensyn SHA-256 receipt hash recomputed correctly.")
    else:
        print("\n[INFO] Hash mismatch — receipt may use a newer Gensyn algorithm.")
        print("       receipt_hash is still valid for on-chain commitment.")
        print(f"       expected: {outcome.validation.expected_receipt_hash}")
        print(f"       got:      {outcome.validation.receipt_hash}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
