#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNTIME_DIR="${SIGNAL_COUNT_BATTLE_RUNTIME_DIR:-${ROOT_DIR}/.runtime/full-battle}"
JOB_FILE="${1:-${RUNTIME_DIR}/job-after-indexer.json}"
REPORT_FILE="${RUNTIME_DIR}/artifact-replay-report.json"
PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="python"
fi
mkdir -p "$(dirname "${REPORT_FILE}")"

case "${1:-}" in
  -h|--help)
    echo "Usage: scripts/replay_full_battle_artifact.sh [job-json-path]"
    exit 0
    ;;
  *)
    ;;
esac

"${PYTHON}" - "${JOB_FILE}" "${REPORT_FILE}" <<'PY'
import json
import sys
from pathlib import Path

from app.identity.hashing import canonical_json_hash
from app.ree.receipts import parse_ree_receipt
from app.ree.validator import validate_ree_receipt

job_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
if not job_path.exists():
    raise SystemExit(f"Missing job artifact: {job_path}")

job = json.loads(job_path.read_text(encoding="utf-8"))
metadata = job.get("run_metadata") or {}
attestations = [
    item
    for item in metadata.get("verification_attestations", [])
    if isinstance(item, dict)
]
responses = {
    str(item.get("node_role", "")): item
    for item in metadata.get("specialist_responses", [])
    if isinstance(item, dict)
}
chain_receipts = [
    item for item in metadata.get("chain_receipts", []) if isinstance(item, dict)
]

output_items = []
for attestation in attestations:
    role = str(attestation.get("node_role", ""))
    expected_hash = str(attestation.get("output_hash") or "")
    response = responses.get(role)
    if not expected_hash:
        status = "missing"
        recomputed = ""
        detail = "no attested output hash"
    elif response is None:
        status = "present_only"
        recomputed = ""
        detail = "old artifact lacks specialist_responses payload"
    else:
        recomputed = canonical_json_hash(response)
        status = "verified" if recomputed == expected_hash else "failed"
        detail = "recomputed from specialist_responses"
    output_items.append(
        {
            "role": role,
            "status": status,
            "output_hash": expected_hash,
            "recomputed_output_hash": recomputed,
            "detail": detail,
        }
    )

ree_items = []
for attestation in attestations:
    role = str(attestation.get("node_role", ""))
    receipt_hash = str(attestation.get("ree_receipt_hash") or "")
    if not (receipt_hash or attestation.get("receipt_status")):
        continue
    source = attestation.get("ree_receipt_body") or attestation.get("ree_receipt_path")
    if source is None:
        ree_items.append(
            {
                "role": role,
                "status": "present_only",
                "receipt_hash": receipt_hash,
                "detail": "old artifact lacks REE receipt body/path",
            }
        )
        continue
    try:
        receipt = parse_ree_receipt(source)
        validation = validate_ree_receipt(receipt)
    except Exception as exc:
        ree_items.append(
            {
                "role": role,
                "status": "failed",
                "receipt_hash": receipt_hash,
                "detail": f"receipt parse failed: {exc}",
            }
        )
        continue
    hash_matches_metadata = (
        not receipt_hash or receipt.receipt_hash.lower() == receipt_hash.lower()
    )
    ree_items.append(
        {
            "role": role,
            "status": "validated"
            if validation.matches and hash_matches_metadata
            else "failed",
            "receipt_hash": receipt_hash or receipt.receipt_hash,
            "recomputed_receipt_hash": validation.expected_receipt_hash,
            "detail": "recomputed from REE receipt material",
        }
    )

chain_items = [
    {
        "kind": str(receipt.get("kind", "")),
        "role": str(receipt.get("role", "")),
        "status": "present_only",
        "tx_hash": str(receipt.get("tx_hash", "")),
        "detail": "saved artifact replay does not query RPC",
    }
    for receipt in chain_receipts
    if receipt.get("tx_hash")
]

report = {
    "job_id": job.get("job_id"),
    "source": str(job_path),
    "output_hashes": output_items,
    "ree": ree_items,
    "chain": chain_items,
    "limits": [
        "present_only means the saved artifact lacks material needed for repeat validation",
        "chain replay does not query RPC; use verify_latest_artifact.sh with a running proof console for live /verify",
    ],
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(f"OK replayed saved artifact: {job.get('job_id')}")
print(f"OK wrote {report_path}")
if any(item["status"] == "failed" for item in output_items + ree_items):
    raise SystemExit("Saved artifact replay found failed checks")
PY
