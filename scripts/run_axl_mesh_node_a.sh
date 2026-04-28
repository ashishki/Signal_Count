#!/usr/bin/env bash
set -euo pipefail

MESH_DIR="${MESH_DIR:-/tmp/signal-count-axl-mesh}"
AXL_IMAGE="${AXL_IMAGE:-gensyn-axl-local}"
AXL_CONTAINER_NAME="${AXL_CONTAINER_NAME:-}"

if [[ ! -f "${MESH_DIR}/node-a.json" ]]; then
  echo "Missing ${MESH_DIR}/node-a.json. Run scripts/prepare_axl_mesh_demo.sh first." >&2
  exit 1
fi

NAME_ARGS=()
if [[ -n "${AXL_CONTAINER_NAME}" ]]; then
  NAME_ARGS=(--name "${AXL_CONTAINER_NAME}")
fi

exec docker run --rm --network host \
  "${NAME_ARGS[@]}" \
  -v "${MESH_DIR}:/mesh:ro" \
  "${AXL_IMAGE}" \
  -config /mesh/node-a.json
