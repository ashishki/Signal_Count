#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNTIME_DIR="${SIGNAL_COUNT_BATTLE_RUNTIME_DIR:-${ROOT_DIR}/.runtime/full-battle}"
APP_URL="${SIGNAL_COUNT_PROOF_CONSOLE_URL:-http://127.0.0.1:8004}"
REQUIRE_LIVE=0

case "${1:-}" in
  --require-live)
    REQUIRE_LIVE=1
    ;;
  -h|--help)
    echo "Usage: scripts/verify_latest_artifact.sh [--require-live]"
    exit 0
    ;;
  "")
    ;;
  *)
    echo "Unknown argument: $1" >&2
    echo "Usage: scripts/verify_latest_artifact.sh [--require-live]" >&2
    exit 2
    ;;
esac

PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="python"
fi

REPORT_FILE="${RUNTIME_DIR}/rehearsal-report.json"
VERIFY_FILE="${RUNTIME_DIR}/verify-live.json"

echo "Signal Count latest artifact rehearsal"
echo "Runtime: ${RUNTIME_DIR}"
echo "Proof console: ${APP_URL}"

"${PYTHON}" - "${RUNTIME_DIR}" <<'PY'
import json
import sys
from pathlib import Path

runtime = Path(sys.argv[1])
required = [
    "summary.txt",
    "job-after-indexer.json",
    "index-after-indexer.html",
    "signal_count.db",
]
missing = [name for name in required if not (runtime / name).exists()]
if missing:
    raise SystemExit(f"Missing full-battle artifacts: {', '.join(missing)}")

job = json.loads((runtime / "job-after-indexer.json").read_text(encoding="utf-8"))
metadata = job.get("run_metadata") or {}
attestations = metadata.get("verification_attestations") or []
chain_receipts = metadata.get("chain_receipts") or []
completed_roles = metadata.get("completed_roles") or []
risk_attestation = next(
    (
        item
        for item in attestations
        if isinstance(item, dict) and item.get("node_role") == "risk"
    ),
    {},
)

checks = {
    "job_completed": job.get("status") == "completed",
    "roles_completed": set(completed_roles) >= {"regime", "narrative", "risk"},
    "attestations_present": len(attestations) >= 3,
    "chain_receipts_present": len(chain_receipts) >= 1,
    "risk_ree_validated": risk_attestation.get("receipt_status") == "validated",
    "index_html_present": (runtime / "index-after-indexer.html").stat().st_size > 0,
    "database_present": (runtime / "signal_count.db").stat().st_size > 0,
}
failed = [name for name, passed in checks.items() if not passed]
report = {
    "mode": "artifact-only",
    "job_id": job.get("job_id"),
    "checks": checks,
    "chain_receipt_count": len(chain_receipts),
    "attestation_count": len(attestations),
    "completed_roles": completed_roles,
}
(runtime / "rehearsal-report.json").write_text(
    json.dumps(report, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
if failed:
    raise SystemExit(f"Artifact rehearsal checks failed: {', '.join(failed)}")
print(f"OK artifact checks passed for job {job.get('job_id')}")
print(f"OK wrote {runtime / 'rehearsal-report.json'}")
PY

JOB_ID="$("${PYTHON}" - "${RUNTIME_DIR}/job-after-indexer.json" <<'PY'
import json
import sys
from pathlib import Path

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")).get("job_id", ""))
PY
)"

if [[ -z "${JOB_ID}" ]]; then
  echo "FAIL job_id missing from job-after-indexer.json" >&2
  exit 1
fi

if curl -fsS "${APP_URL}/health" >/dev/null 2>&1; then
  curl -fsS "${APP_URL}/jobs/${JOB_ID}/verify" >"${VERIFY_FILE}"
  "${PYTHON}" - "${VERIFY_FILE}" "${REPORT_FILE}" <<'PY'
import json
import sys
from pathlib import Path

verify_path = Path(sys.argv[1])
report_path = Path(sys.argv[2])
verify = json.loads(verify_path.read_text(encoding="utf-8"))
checks = verify.get("checks") or {}
required_groups = ["output_hashes", "attestations", "ree", "chain"]
missing_groups = [group for group in required_groups if group not in checks]
if missing_groups:
    raise SystemExit(f"Live verify bundle missing groups: {', '.join(missing_groups)}")
bad_statuses = {
    group: checks[group].get("status")
    for group in required_groups
    if checks[group].get("status") in {"failed", "missing"}
}
report = json.loads(report_path.read_text(encoding="utf-8"))
report["mode"] = "artifact-and-live"
report["live_verify"] = {
    "status": verify.get("status"),
    "groups": {group: checks[group].get("status") for group in required_groups},
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
if bad_statuses:
    raise SystemExit(f"Live verify checks failed: {bad_statuses}")
print(f"OK live verify passed: {verify.get('status')}")
PY
else
  if (( REQUIRE_LIVE )); then
    echo "FAIL proof console is not reachable at ${APP_URL}" >&2
    exit 1
  fi
  echo "WARN proof console is not reachable; artifact-only rehearsal passed"
fi

echo "OK latest artifact rehearsal complete"
