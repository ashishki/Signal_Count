#!/usr/bin/env bash
set -euo pipefail

AXL_REMOTE_PEER_ID="${AXL_REMOTE_PEER_ID:-}"
APP_PORT="${APP_PORT:-8004}"

if [[ -z "${AXL_REMOTE_PEER_ID}" ]]; then
  echo "AXL_REMOTE_PEER_ID is required. Read it from http://127.0.0.1:9024/topology." >&2
  exit 1
fi

export SIGNAL_COUNT_DEMO_LLM="${SIGNAL_COUNT_DEMO_LLM:-1}"
export AXL_LOCAL_BASE_URL="${AXL_LOCAL_BASE_URL:-http://127.0.0.1:9022}"
export AXL_MCP_ROUTER_URL="${AXL_MCP_ROUTER_URL:-http://127.0.0.1:9014}"
export REGIME_PEER_ID="${REGIME_PEER_ID:-${AXL_REMOTE_PEER_ID}}"
export NARRATIVE_PEER_ID="${NARRATIVE_PEER_ID:-${AXL_REMOTE_PEER_ID}}"
export RISK_PEER_ID="${RISK_PEER_ID:-${AXL_REMOTE_PEER_ID}}"

exec uvicorn app.main:app --host 127.0.0.1 --port "${APP_PORT}"
