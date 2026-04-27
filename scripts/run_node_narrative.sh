#!/usr/bin/env bash
set -euo pipefail

export NODE_ROLE=narrative
export NODE_SERVICE_NAME="${NODE_SERVICE_NAME:-narrative_analyst}"
export NODE_PUBLIC_URL="${NODE_PUBLIC_URL:-http://127.0.0.1:7102}"
exec uvicorn app.nodes.server:app --host 127.0.0.1 --port 7102
