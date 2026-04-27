#!/usr/bin/env bash
set -euo pipefail

AXL_LOCAL_BASE_URL="${AXL_LOCAL_BASE_URL:-http://127.0.0.1:9002}"
AXL_MCP_ROUTER_URL="${AXL_MCP_ROUTER_URL:-http://127.0.0.1:9003}"

echo "AXL topology:"
curl -fsS "${AXL_LOCAL_BASE_URL}/topology"
echo
echo "MCP services:"
curl -fsS "${AXL_MCP_ROUTER_URL}/services"
echo
