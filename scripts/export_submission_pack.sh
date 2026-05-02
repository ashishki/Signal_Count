#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNTIME_DIR="${SIGNAL_COUNT_BATTLE_RUNTIME_DIR:-${ROOT_DIR}/.runtime/full-battle}"
EXPORT_ROOT="${SIGNAL_COUNT_SUBMISSION_EXPORT_DIR:-${ROOT_DIR}/.runtime/submission-pack}"
APP_URL="${SIGNAL_COUNT_PROOF_CONSOLE_URL:-http://127.0.0.1:8004}"
STAMP="$(date +%Y%m%d_%H%M%S)"
PACK_DIR="${EXPORT_ROOT}/${STAMP}"
PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="python"
fi

case "${1:-}" in
  -h|--help)
    echo "Usage: scripts/export_submission_pack.sh"
    exit 0
    ;;
  "")
    ;;
  *)
    echo "Unknown argument: $1" >&2
    echo "Usage: scripts/export_submission_pack.sh" >&2
    exit 2
    ;;
esac

mkdir -p "${PACK_DIR}"

copy_if_present() {
  local source="$1"
  local target="$2"
  if [[ -f "${source}" ]]; then
    cp "${source}" "${target}"
  fi
}

copy_if_present "${RUNTIME_DIR}/summary.txt" "${PACK_DIR}/summary.txt"
copy_if_present "${RUNTIME_DIR}/job.json" "${PACK_DIR}/job.json"
copy_if_present "${RUNTIME_DIR}/job-after-indexer.json" "${PACK_DIR}/job-after-indexer.json"
copy_if_present "${RUNTIME_DIR}/index-after-indexer.html" "${PACK_DIR}/index-after-indexer.html"
copy_if_present "${RUNTIME_DIR}/rehearsal-report.json" "${PACK_DIR}/rehearsal-report.json"
copy_if_present "${RUNTIME_DIR}/verify-live.json" "${PACK_DIR}/verify-live.json"

"${PYTHON}" - "${RUNTIME_DIR}" "${PACK_DIR}" "${APP_URL}" <<'PY'
import json
import sys
from pathlib import Path

runtime = Path(sys.argv[1])
pack = Path(sys.argv[2])
app_url = sys.argv[3].rstrip("/")
job_path = runtime / "job-after-indexer.json"
if not job_path.exists():
    raise SystemExit(f"Missing required artifact: {job_path}")

job = json.loads(job_path.read_text(encoding="utf-8"))
metadata = job.get("run_metadata") or {}
chain_receipts = [
    item for item in metadata.get("chain_receipts", []) if isinstance(item, dict)
]
attestations = [
    item
    for item in metadata.get("verification_attestations", [])
    if isinstance(item, dict)
]
tx_links = [
    str(item.get("explorer_url"))
    for item in chain_receipts
    if item.get("explorer_url")
]
(pack / "tx-links.txt").write_text("\n".join(tx_links) + ("\n" if tx_links else ""))

verify_url = f"{app_url}/jobs/{job.get('job_id')}/verify"
notes = [
    "# Signal Count Submission Pack",
    "",
    f"- Job ID: `{job.get('job_id')}`",
    f"- Job status: `{job.get('status')}`",
    f"- Verify URL: `{verify_url}`",
    f"- Chain receipts: `{len(chain_receipts)}`",
    f"- Verifier attestations: `{len(attestations)}`",
    f"- Completed roles: `{', '.join(metadata.get('completed_roles', []))}`",
    f"- REE policy: `{metadata.get('ree_policy', '')}`",
    "",
    "## Included Files",
    "",
    "- `summary.txt`",
    "- `job.json`",
    "- `job-after-indexer.json`",
    "- `index-after-indexer.html`",
    "- `rehearsal-report.json` when available",
    "- `verify-live.json` when available",
    "- `tx-links.txt`",
    "",
    "## Claim Boundaries",
    "",
    "- Offline fixtures must not be described as live market/news retrieval.",
    "- Same-machine AXL mesh must not be described as remote multi-machine execution.",
    "- REE `validated` means local receipt consistency, not full remote re-execution.",
    "- Chain receipt checks are limited to stored tx evidence and configured RPC receipt status.",
]
(pack / "SUBMISSION_NOTES.md").write_text("\n".join(notes) + "\n", encoding="utf-8")

manifest = {
    "job_id": job.get("job_id"),
    "pack_dir": str(pack),
    "verify_url": verify_url,
    "chain_receipt_count": len(chain_receipts),
    "attestation_count": len(attestations),
    "tx_links": tx_links,
}
(pack / "manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(f"OK exported submission pack: {pack}")
PY
