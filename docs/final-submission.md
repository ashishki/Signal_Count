# Final Submission Checklist — Signal Count

## Demo Narrative

```text
This is not an agent town. It is a proof layer for agent work:
distributed execution through AXL, reproducible inference through REE,
and public attribution through Gensyn Testnet receipts.
```

## Required Evidence

| Evidence | Status | Where to Show |
| --- | --- | --- |
| Registered specialist roles | Ready | MCP router services and proof console run evidence |
| AXL peer IDs and dispatch targets | Ready | `Proof Ledger`, topology snapshot, mesh check output |
| Specialist output hashes | Ready | `Task Trace` and verifier attestations |
| Verifier attestation and score | Ready | run metadata and `Task Trace` |
| REE receipt hash/status | Ready when REE is enabled for the run | risk specialist response and `Task Trace` |
| Gensyn Testnet tx links | Ready when chain receipts are configured | `Task Trace`, `chain_receipts`, explorer links |
| Memo evidence source links | Ready | final memo supporting/opposing evidence bullets |
| Reputation/test reward evidence | Ready when reputation vault is configured | `chain_receipts`, leaderboard, indexed events |
| Event-indexed recovery | Ready | `ChainIndexerScheduler` and projection tests |

## Commands to Run Before Recording

```bash
python -m pytest tests/ -q --tb=short
forge test
ruff check .
ruff format --check .
```

Current verified baseline:

```text
python pytest: 119 passed
forge test: 6 passed
ruff check: pass
ruff format check: pass
```

## Demo Modes

Use offline preview only for stable UI screenshots:

```bash
scripts/run_offline_demo.sh
```

Use live local AXL mode to show the real local bridge and MCP router:

```bash
scripts/check_axl.sh
scripts/run_app_live.sh
```

Use same-machine multi-peer mode for the strongest AXL evidence:

```bash
scripts/prepare_axl_mesh_demo.sh
scripts/run_axl_mesh_router.sh
scripts/run_axl_mesh_node_a.sh
scripts/run_axl_mesh_node_b.sh
scripts/check_axl_mesh.sh
```

Use the one-command full battle runner for the final video capture:

```bash
scripts/run_full_battle_demo.sh
```

It produces presentation-friendly terminal logs, starts the proof console at
`http://127.0.0.1:8004`, and writes a plain evidence summary to
`.runtime/full-battle/summary.txt`.

Use the REE E2E script when recording reproducible inference evidence:

```bash
REE_SH=/tmp/gensyn-ree/ree.sh REE_CPU_ONLY=1 .venv/bin/python scripts/verify_ree_e2e.py
```

## Claims to Make

- Signal Count routes specialist work through AXL and records per-role dispatch
  evidence.
- Signal Count produces signed/verifier-scored specialist evidence and a
  source-linked memo.
- Signal Count can attach real Gensyn REE receipt metadata to the risk
  specialist path.
- Signal Count can record and display Gensyn Testnet task, contribution, and
  reputation receipts when chain writing is configured.
- Signal Count can rebuild chain-backed projections from indexed contract
  events after restart.
- Signal Count includes a proof-console UI that shows capability state, mesh
  visualization, run timeline, final memo, task trace, REE status, explorer
  links, reputation evidence, and indexed event counts.

## Claims to Avoid

- Do not claim remote multi-machine AXL execution unless the demo actually runs
  across separate hosts.
- Do not claim ERC20, USDC, stablecoin, or real-money rewards.
- Do not claim native test-ETH payout as anything beyond tiny capped testnet
  evidence.
- Do not claim full archival chain reorg rollback beyond the configured repair
  window.
- Do not describe offline preview fixtures as live AXL, REE, or Gensyn Testnet
  evidence.
