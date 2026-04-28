#!/usr/bin/env bash
set -euo pipefail

AXL_REMOTE_ROUTER_PORT="${AXL_REMOTE_ROUTER_PORT:-9014}"
PYTHON="${PYTHON:-python}"

exec "${PYTHON}" -m mcp_routing.mcp_router --port "${AXL_REMOTE_ROUTER_PORT}"
