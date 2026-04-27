#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"
PORT="${2:-}"
AXL_REMOTE_PEER_ID="${AXL_REMOTE_PEER_ID:-}"

if [[ -z "${ROLE}" ]]; then
  echo "Usage: AXL_REMOTE_PEER_ID=<node-b-public-key> $0 <regime|narrative|risk> [port]" >&2
  exit 1
fi

if [[ -z "${AXL_REMOTE_PEER_ID}" ]]; then
  echo "AXL_REMOTE_PEER_ID is required. Read it from http://127.0.0.1:9024/topology." >&2
  exit 1
fi

case "${ROLE}" in
  regime)
    PORT="${PORT:-7161}"
    export NODE_SERVICE_NAME="${NODE_SERVICE_NAME:-regime_analyst}"
    export REGIME_PEER_ID="${AXL_REMOTE_PEER_ID}"
    ;;
  narrative)
    PORT="${PORT:-7162}"
    export NODE_SERVICE_NAME="${NODE_SERVICE_NAME:-narrative_analyst}"
    export NARRATIVE_PEER_ID="${AXL_REMOTE_PEER_ID}"
    ;;
  risk)
    PORT="${PORT:-7163}"
    export NODE_SERVICE_NAME="${NODE_SERVICE_NAME:-risk_analyst}"
    export RISK_PEER_ID="${AXL_REMOTE_PEER_ID}"
    ;;
  *)
    echo "Unsupported role: ${ROLE}. Expected regime, narrative, or risk." >&2
    exit 1
    ;;
esac

export SIGNAL_COUNT_DEMO_LLM="${SIGNAL_COUNT_DEMO_LLM:-1}"
export AXL_MCP_ROUTER_URL="${AXL_MCP_ROUTER_URL:-http://127.0.0.1:9014}"
export NODE_ROLE="${ROLE}"
export NODE_PUBLIC_URL="${NODE_PUBLIC_URL:-http://127.0.0.1:${PORT}}"

exec uvicorn app.nodes.server:app --host 127.0.0.1 --port "${PORT}"
