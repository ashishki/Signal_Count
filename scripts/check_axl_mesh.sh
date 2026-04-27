#!/usr/bin/env bash
set -euo pipefail

AXL_COORDINATOR_BASE_URL="${AXL_COORDINATOR_BASE_URL:-http://127.0.0.1:9022}"
AXL_REMOTE_BASE_URL="${AXL_REMOTE_BASE_URL:-http://127.0.0.1:9024}"
AXL_REMOTE_ROUTER_URL="${AXL_REMOTE_ROUTER_URL:-http://127.0.0.1:9014}"

echo "Coordinator AXL node topology:"
curl -fsS "${AXL_COORDINATOR_BASE_URL}/topology"
echo

echo "Remote AXL node topology:"
curl -fsS "${AXL_REMOTE_BASE_URL}/topology"
echo

echo "Remote MCP services:"
curl -fsS "${AXL_REMOTE_ROUTER_URL}/services"
echo
