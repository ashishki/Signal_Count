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

## Full Battle Demo

Use this path for the recorded terminal segment. It runs the full stack in one
script and prints video-friendly logs with sections for preflight, AXL mesh,
specialist services, app startup, live job submission, indexer, evidence
summary, and shutdown instructions.

```bash
scripts/run_full_battle_demo.sh
```

The script uses:

- Local two-node AXL mesh.
- MCP router and three specialist services.
- Coordinator app on `http://127.0.0.1:8004`.
- Gensyn REE for the risk specialist path.
- Gensyn Testnet task/contribution/reputation receipts.
- Tiny capped native test-ETH payouts of `1000000000 wei` per role by default.
- One-shot chain indexer after the run completes.

Artifacts are written under:

```text
.runtime/full-battle/
```

Important files:

- `summary.txt` - plain-text run summary without terminal color codes.
- `job.json` - completed job immediately after submission.
- `job-after-indexer.json` - job fetched after the indexer run.
- `index-after-indexer.html` - rendered proof console after indexing.
- `logs/` - per-process logs.

The script leaves the viewer running for screen capture. Stop all demo processes
after recording:

```bash
scripts/stop_full_battle_demo.sh
```

Current verified full-battle reference run from April 28, 2026:

- Job ID: `c033560c-7a30-4668-87f4-a75559d06475`.
- Runtime: `406s` end to end.
- Live job completed at `+397s`; the remaining time was one-shot indexing and
  evidence summary generation.
- Roles: `regime`, `narrative`, and `risk` completed.
- REE status: `validated`.
- Chain receipts: 7 transaction receipts.
- Indexed projection after replay: `tasks=6`, `contributions=15`,
  `verifications=0`, `reputation=15`.

## Screenshot Set

Capture these screenshots in order:

1. Home and thesis input.
2. Filled thesis form.
3. Latest completed job with `partial=false`.
4. Scenario table.
5. Risks and invalidation conditions.
6. Memo evidence bullets with visible source metadata.
7. `Task Trace` ledger with AXL peer, wallet, output hash, REE status, and tx
   link if chain receipts are configured.
8. Run evidence, dispatch targets, and topology public keys.
9. Reputation/test payout receipt evidence if enabled for testnet.
10. Proof console hero, mesh visualization, capability strip, and tabbed latest
    run panel.

## Video Structure

- 0:00-0:20: what Signal Count does.
- 0:20-0:50: show AXL topology and specialist services.
- 0:50-1:40: show the full battle terminal logs while the live job runs.
- 1:40-2:30: show final memo and source-linked evidence.
- 2:30-3:20: show `Task Trace`, REE receipt status, explorer links, and
  reputation evidence.
- 3:20-3:45: show event-indexed projection/recovery behavior if using the
  indexer in the demo.
- 3:45-4:00: explain why it is decision support, not a trading bot.

## Claim Boundaries

- Offline preview is only for stable UI capture and must stay labelled as
  `offline-demo-preview`.
- Same-machine multi-peer AXL mesh proves distinct local AXL peer identities,
  not remote multi-machine deployment.
- REE should be described as present only when a real receipt exists for the
  run being shown.
- Gensyn Testnet receipt claims require real tx hashes or explorer links.
- Native test-ETH payouts are tiny, capped, opt-in testnet evidence; do not
  describe them as stablecoin or real-money rewards.
