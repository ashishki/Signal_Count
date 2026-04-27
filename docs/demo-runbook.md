# Signal Count Demo Runbook

## Offline Preview

Use this mode for stable screenshots and UI walkthroughs when a live AXL mesh is
not running.

```bash
scripts/run_offline_demo.sh
```

Open:

```text
http://127.0.0.1:8000
```

The topology section should show:

```text
Mode: offline-demo-preview
```

## Partial-Failure Preview

Use this mode to demonstrate degraded execution without pretending the missing
node answered:

```bash
scripts/run_offline_partial_demo.sh
```

Expected UI evidence:

- The memo shows a partial coverage warning.
- `Run Metadata` lists `risk` in `missing_roles`.
- `Run Evidence` shows the risk role as timed out.
- The final memo does not invent risk-node provenance.

## Live AXL Mode

Run these commands in separate terminals after the Gensyn AXL node and MCP
router dependencies are available.

```bash
scripts/run_node_regime.sh
scripts/run_node_narrative.sh
scripts/run_node_risk.sh
scripts/run_app_live.sh
```

Check the AXL state:

```bash
scripts/check_axl.sh
```

Expected evidence for a successful local AXL run:

- The MCP router lists `regime_analyst`, `narrative_analyst`, and `risk_analyst`
  as registered services.
- The AXL topology endpoint returns `our_public_key`.
- A completed job shows `transport=axl-mcp`.
- `Run Evidence` shows all three roles as `completed`.
- Each dispatch target uses `/mcp/{axl_public_key}/{service_name}`.
- `Topology Snapshot` shows the same AXL public key.

Current verified scope:

- Verified: local Gensyn AXL node -> MCP router -> specialist `/mcp` services.
- Verified: coordinator creates a full completed job through `axl-mcp`.
- Not claimed: remote multi-machine AXL mesh with separate public keys.

If the UI returns a server error after a live run, check the topology shape. The
live AXL node may return `peers=null`; the UI now handles that shape and falls
back to `our_public_key` for the local peer display.

## Multi-Peer AXL Mesh Mode

Use this mode for the strongest sponsor demo. It runs two separate AXL nodes
with distinct public keys on the same machine:

- Node A is the coordinator bridge at `http://127.0.0.1:9022`.
- Node B is the remote specialist peer at `http://127.0.0.1:9024`.
- Node B registers specialist services with its own MCP router at
  `http://127.0.0.1:9014`.

Prepare node keys and configs:

```bash
scripts/prepare_axl_mesh_demo.sh
```

Run these in separate terminals:

```bash
scripts/run_axl_mesh_router.sh
scripts/run_axl_mesh_node_a.sh
scripts/run_axl_mesh_node_b.sh
```

Read Node B's public key:

```bash
curl -fsS http://127.0.0.1:9024/topology
```

Export it for the specialist and app terminals:

```bash
export AXL_REMOTE_PEER_ID="<node-b-our_public_key>"
```

Run the specialist services behind Node B's router:

```bash
scripts/run_axl_mesh_specialist.sh regime
scripts/run_axl_mesh_specialist.sh narrative
scripts/run_axl_mesh_specialist.sh risk
```

Run the coordinator app through Node A:

```bash
scripts/run_app_mesh_live.sh
```

Open:

```text
http://127.0.0.1:8004
```

Check the mesh state:

```bash
scripts/check_axl_mesh.sh
```

Expected mesh evidence:

- Coordinator topology shows Node A `our_public_key`.
- Coordinator topology lists Node B as an `up` peer with a different
  `public_key`.
- Remote topology shows Node B `our_public_key`.
- Remote MCP router lists all three specialist services.
- Completed jobs show `AXL_LOCAL_BASE_URL=http://127.0.0.1:9022`.
- `Run Evidence` dispatch targets use Node B's public key.
- `partial=false` and all three roles are `completed`.

This proves a local multi-peer AXL mesh with distinct peer identities. It is
stronger than the single-node bridge demo, but it is still a local same-machine
mesh unless run across separate machines.

## Screenshot Set

Capture these six screenshots in order:

1. Home and thesis input.
2. Filled thesis form.
3. Latest completed job with `partial=false`.
4. Scenario table.
5. Risks and invalidation conditions.
6. Run evidence, dispatch targets, and topology public keys.

## Video Structure

- 0:00-0:20: what Signal Count does.
- 0:20-0:50: show AXL topology and specialist services.
- 0:50-1:40: submit or replay a thesis.
- 1:40-2:40: show final memo.
- 2:40-3:30: show run evidence and node participation.
- 3:30-4:00: explain why it is decision support, not a trading bot.
