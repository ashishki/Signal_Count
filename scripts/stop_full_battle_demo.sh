#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${SIGNAL_COUNT_BATTLE_RUNTIME_DIR:-${ROOT_DIR}/.runtime/full-battle}"
PIDS_FILE="${RUNTIME_DIR}/pids"

if [[ ! -f "${PIDS_FILE}" ]]; then
  echo "No full battle PID file found at ${PIDS_FILE}"
  exit 0
fi

tac "${PIDS_FILE}" | while read -r pid; do
  [[ -z "${pid}" ]] && continue
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
  fi
done

sleep 1

tac "${PIDS_FILE}" | while read -r pid; do
  [[ -z "${pid}" ]] && continue
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
done

rm -f "${PIDS_FILE}"

for container in signal-count-axl-node-a signal-count-axl-node-b; do
  if docker ps --format '{{.Names}}' | grep -qx "${container}"; then
    docker stop "${container}" >/dev/null 2>&1 || true
  fi
done

echo "Stopped full battle demo processes."
