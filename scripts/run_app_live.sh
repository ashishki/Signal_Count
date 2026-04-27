#!/usr/bin/env bash
set -euo pipefail

export AXL_LOCAL_BASE_URL="${AXL_LOCAL_BASE_URL:-http://127.0.0.1:9002}"
exec uvicorn app.main:app --reload
