# Signal Count

AXL-powered market thesis review for the ETHGlobal OpenAgents / Gensyn track.

Signal Count is not a trading bot. A user submits one market thesis, an asset,
and a time horizon. A coordinator dispatches structured analysis requests to
specialist services through AXL, collects their responses, and produces an
auditable risk memo with scenarios, catalysts, risks, invalidation triggers,
and provenance.

## What It Does

- Accepts a single market thesis through a FastAPI API or minimal demo UI.
- Routes work to specialist roles for regime, narrative, and risk analysis.
- Records node participation, peer IDs, latency, and topology snapshots.
- Produces a structured memo instead of a generic chat response.
- Degrades explicitly when a specialist is unavailable.

## Why AXL

The coordinator is designed to talk to its local AXL HTTP bridge and address
specialist services by peer ID and service name:

```text
/mcp/{peer_id}/{service_name}
```

That keeps the swarm boundary visible in the product: the demo can show which
peers participated in a run, rather than hiding all analysis inside one local
process.

## Architecture

```text
User / Demo UI
  |
FastAPI API
  |
Coordinator
  |
Local AXL bridge
  |
AXL specialist peers
  |-- Regime analyst
  |-- Narrative analyst
  |-- Risk analyst
  |
Memo synthesis + provenance ledger
```

## Repository Layout

```text
app/
  api/              FastAPI routes
  axl/              AXL registry and client layer
  coordinator/      Dispatch and memo synthesis workflow
  integrations/     LLM, market data, and news adapters
  nodes/            Specialist service implementations
  observability/    Metrics, tracing, provenance records
  rendering/        Memo rendering
  schemas/          Pydantic contracts
  store/            SQLite-backed job store
  templates/        Minimal demo UI
docs/
  ARCHITECTURE.md   Public architecture notes
  spec.md           Product specification
tests/              Unit and integration tests
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt -e .
```

## Run

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Offline Demo Preview

Use this mode when capturing stable screenshots without a live AXL bridge:

```bash
scripts/run_offline_demo.sh
```

The UI labels the topology as `offline-demo-preview` so it is not confused with
a live AXL run.

To preview partial-failure behavior without a live AXL mesh:

```bash
scripts/run_offline_partial_demo.sh
```

By default this forces the `risk` specialist to time out and verifies that the
memo is marked as partial instead of fabricating a missing node response.

## Live AXL Mode

Live mode expects the Gensyn AXL node and MCP router to be running. The
specialist server registers itself with the local MCP router using
`POST /register` and exposes `POST /mcp` for routed specialist requests.

Start the AXL MCP router first:

```bash
python -m mcp_routing.mcp_router --port 9003
```

Then run the three specialist services in separate terminals:

```bash
scripts/run_node_regime.sh
```

```bash
scripts/run_node_narrative.sh
```

```bash
scripts/run_node_risk.sh
```

Finally run the coordinator app with its local AXL bridge URL:

```bash
scripts/run_app_live.sh
```

Useful checks:

```bash
scripts/check_axl.sh
```

### Verified Local AXL Run

The current implementation has been verified against a locally running Gensyn
AXL node, MCP router, and three specialist services. The coordinator submitted a
job through:

```text
/mcp/{axl_public_key}/{service_name}
```

and recorded all three roles as completed with `transport=axl-mcp`:

```text
regime -> regime_analyst
narrative -> narrative_analyst
risk -> risk_analyst
```

This verifies the local AXL bridge plus MCP router path. It should not be
overstated as a multi-machine remote mesh unless separate AXL nodes with
distinct public keys are also running.

### Multi-Peer AXL Mesh Demo

For the strongest Gensyn demo, Signal Count can run with two local AXL nodes
that have distinct public keys:

```text
Coordinator app -> AXL node A -> AXL node B -> MCP router B -> specialist services
```

Prepare the mesh configs:

```bash
scripts/prepare_axl_mesh_demo.sh
```

Start the mesh in separate terminals:

```bash
scripts/run_axl_mesh_router.sh
scripts/run_axl_mesh_node_a.sh
scripts/run_axl_mesh_node_b.sh
```

Read the remote peer ID from Node B:

```bash
curl -fsS http://127.0.0.1:9024/topology
```

Then export `AXL_REMOTE_PEER_ID` and start the services:

```bash
export AXL_REMOTE_PEER_ID="<node-b-our_public_key>"
scripts/run_axl_mesh_specialist.sh regime
scripts/run_axl_mesh_specialist.sh narrative
scripts/run_axl_mesh_specialist.sh risk
scripts/run_app_mesh_live.sh
```

Check the mesh:

```bash
scripts/check_axl_mesh.sh
```

In this mode the coordinator uses Node A as its local bridge
(`AXL_LOCAL_BASE_URL=http://127.0.0.1:9022`) while the run evidence points each
specialist dispatch at Node B's public key. This demonstrates separate AXL peer
identities without claiming a remote multi-machine deployment.

## Test

```bash
python -m pytest tests/ -q --tb=short
ruff check app/ tests/
ruff format --check app/ tests/
```

Current local verification:

```text
60 passed
ruff check app tests: pass
ruff format --check app tests: pass
```

## Submission Notes

- Category: AI
- Emoji: ⚖️
- Short description: AXL-powered analyst swarm that stress-tests market theses
  into auditable risk memos.

## AI Usage

AI tools were used during development for implementation assistance, test
iteration, and wording support. Product design, architecture choices, scope
control, AXL integration boundaries, and final submission decisions are
human-directed.
