# Architecture — Signal Count

## Overview

Signal Count is a backend-first market thesis review system. A user submits one
thesis, an asset, and a horizon. The coordinator dispatches structured requests
through AXL to specialist services and synthesizes the responses into a compact
risk memo.

The product is decision support, not trading execution or market prediction.

## Runtime Shape

```text
User / Demo UI
  |
FastAPI API
  |
Coordinator
  |
AXL local HTTP bridge
  |
AXL peer services
  |-- Regime analyst
  |-- Narrative analyst
  |-- Risk analyst
  |
Memo synthesis
  |
SQLite job store + provenance ledger
```

## Main Components

| Component | Location | Responsibility |
| --- | --- | --- |
| API | `app/api/` | Health, job submission, demo page routes |
| AXL client | `app/axl/` | Local bridge calls, peer/service addressing, topology fetch |
| Coordinator | `app/coordinator/` | Fetch context, fan out specialist calls, collect responses |
| Specialist services | `app/nodes/` | Regime, narrative, and risk analysis |
| Schemas | `app/schemas/` | Pydantic request, response, memo, and provenance contracts |
| Persistence | `app/store/` | SQLite job and memo storage |
| Rendering | `app/rendering/` | HTML rendering for the demo memo |
| Observability | `app/observability/` | Tracing, metrics, node execution records |

## AXL Integration Boundary

The coordinator does not call specialist hosts directly in the production path.
It resolves a specialist role to a configured AXL peer ID and service name, then
builds an MCP route through the local AXL bridge:

```text
{AXL_LOCAL_BASE_URL}/mcp/{peer_id}/{service_name}
```

Each job also records a topology snapshot and per-node execution records so a
demo can show which peers participated, whether any role failed, and how long
each specialist took.

Payloads crossing this boundary are transport-safe JSON data only. Runtime
objects such as Python LLM client instances stay inside the receiving process.
This matters because the live AXL path serializes requests over HTTP; an
in-process object in the payload would work only in a fake local workflow and
fail through the real bridge.

The single-node live verification proves:

- coordinator -> local AXL bridge
- local AXL bridge -> MCP router
- MCP router -> specialist `/mcp` endpoints
- job ledger recording `axl-mcp` transport and dispatch targets

The multi-peer mesh demo strengthens that path:

```text
Coordinator app
  |
AXL node A: local bridge
  |
AXL node B: remote peer identity
  |
MCP router B
  |
regime / narrative / risk specialist services
```

In that mode, `AXL_LOCAL_BASE_URL` points to Node A while role peer IDs point to
Node B. The topology snapshot shows both public keys, and dispatch targets use
Node B's public key. This is a real local AXL peer separation. It should still
be described as a same-machine mesh unless the nodes are deployed on separate
machines.

## Specialist Node Server

`app/nodes/server.py` provides the AXL-facing process for a specialist node. It
exposes:

- `GET /health` for local service checks.
- `POST /mcp` for routed specialist requests.

On startup the server registers with the AXL MCP router:

```text
POST {AXL_MCP_ROUTER_URL}/register
{
  "service": "<service_name>",
  "endpoint": "<node_public_url>/mcp"
}
```

The same server binary is used for all three roles by changing environment
variables such as `NODE_ROLE`, `NODE_SERVICE_NAME`, and `NODE_PUBLIC_URL`.

## Specialist Roles

| Role | Purpose |
| --- | --- |
| Regime | Interprets market snapshot context and scenario balance |
| Narrative | Reviews recent headlines and possible catalysts |
| Risk | Produces counter-thesis, risks, and invalidation conditions |

## Final Memo

The final memo contains:

- normalized thesis
- bull/base/bear scenario weights
- supporting evidence
- opposing evidence
- catalysts
- risks
- invalidation triggers
- confidence rationale
- specialist provenance
- partial-run warning when a role is unavailable

## Non-Goals

- No trade execution.
- No brokerage or exchange integration.
- No portfolio optimization.
- No generic chatbot interface as the primary product.
- No hidden local fallback that pretends to be a remote AXL peer.
