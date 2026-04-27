#!/usr/bin/env bash
set -euo pipefail

MESH_DIR="${MESH_DIR:-/tmp/signal-count-axl-mesh}"
mkdir -p "${MESH_DIR}"

if [[ ! -f "${MESH_DIR}/node-a.pem" ]]; then
  openssl genpkey -algorithm ed25519 -out "${MESH_DIR}/node-a.pem"
fi

if [[ ! -f "${MESH_DIR}/node-b.pem" ]]; then
  openssl genpkey -algorithm ed25519 -out "${MESH_DIR}/node-b.pem"
fi

cat >"${MESH_DIR}/node-a.json" <<'JSON'
{
  "PrivateKeyPath": "/mesh/node-a.pem",
  "Peers": [],
  "Listen": ["tls://127.0.0.1:9101"],
  "api_port": 9022,
  "bridge_addr": "127.0.0.1",
  "tcp_port": 7010
}
JSON

cat >"${MESH_DIR}/node-b.json" <<'JSON'
{
  "PrivateKeyPath": "/mesh/node-b.pem",
  "Peers": ["tls://127.0.0.1:9101"],
  "Listen": [],
  "api_port": 9024,
  "bridge_addr": "127.0.0.1",
  "tcp_port": 7010,
  "router_addr": "http://127.0.0.1",
  "router_port": 9014
}
JSON

echo "Prepared AXL mesh demo configs in ${MESH_DIR}"
echo "Node A API: http://127.0.0.1:9022"
echo "Node B API: http://127.0.0.1:9024"
echo "Node B MCP router: http://127.0.0.1:9014"
