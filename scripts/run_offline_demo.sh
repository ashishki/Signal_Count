#!/usr/bin/env bash
set -euo pipefail

export SIGNAL_COUNT_OFFLINE_DEMO=1
exec uvicorn app.main:app --reload
