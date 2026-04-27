#!/usr/bin/env bash
set -euo pipefail

export SIGNAL_COUNT_OFFLINE_DEMO=1
export SIGNAL_COUNT_OFFLINE_FAIL_ROLE="${SIGNAL_COUNT_OFFLINE_FAIL_ROLE:-risk}"
exec uvicorn app.main:app --reload
