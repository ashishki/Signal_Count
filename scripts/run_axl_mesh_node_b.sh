#!/usr/bin/env bash
set -euo pipefail

MESH_DIR="${MESH_DIR:-/tmp/signal-count-axl-mesh}"
AXL_IMAGE="${AXL_IMAGE:-gensyn-axl-local}"

if [[ ! -f "${MESH_DIR}/node-b.json" ]]; then
  echo "Missing ${MESH_DIR}/node-b.json. Run scripts/prepare_axl_mesh_demo.sh first." >&2
  exit 1
fi

exec docker run --rm --network host \
  -v "${MESH_DIR}:/mesh:ro" \
  "${AXL_IMAGE}" \
  -config /mesh/node-b.json
