# Final Submission Checklist — Signal Count

## Demo Narrative

```text
Do not trust the memo. Verify every agent behind it:
AXL dispatch shows who did the work, REE receipts show which inference can be
checked, and Gensyn Testnet receipts bind the contribution to public evidence.
```

## Required Evidence

| Evidence | Status | Where to Show |
| --- | --- | --- |
| Registered specialist roles | Ready | MCP router services and proof console run evidence |
| AXL peer IDs and dispatch targets | Ready | `Proof Ledger`, topology snapshot, mesh check output |
| Specialist output hashes | Ready; new jobs can recompute persisted specialist payload hashes in `/verify` | `Task Trace` and verifier attestations |
| Verifier attestation and score | Ready | run metadata and `Task Trace` |
| Active verification action | Ready for stored evidence; RPC tx receipt status verification is implemented when configured | `GET /jobs/{job_id}/verify` and proof-console verify controls |
| REE receipt hash/status | Ready for the latest full-battle run; risk path is `validated`; new REE-backed jobs persist receipt body/path for repeat validation | `Risk REE Proof`, risk specialist response, and `Task Trace` |
| Gensyn Testnet tx links | Ready when chain receipts are configured | `Task Trace`, `chain_receipts`, explorer links |
| Memo evidence source links | Ready; current market/news demo inputs are fixture-labelled, not live-source claims | final memo supporting/opposing evidence bullets and `Source Quality` |
| Reputation/test reward evidence | Ready when reputation vault is configured | `chain_receipts`, leaderboard, indexed events |
| Event-indexed recovery | Ready | `ChainIndexerScheduler` and projection tests |

## Commands to Run Before Recording

```bash
python -m pytest tests/ -q --tb=short
forge test
ruff check .
ruff format --check .
```

Current local baseline from May 2, 2026:

```text
.venv/bin/python pytest: 134 passed, 1 skipped in socket-restricted sandbox
forge test: 6 passed
ruff check: pass
ruff format check: pass
scripts/run_full_battle_demo.sh --preflight-only: passes outside sandbox when
  recording ports are free
```

The latest full-battle artifact is ready for recording. If the saved proof
console is already running on `8004`, stop it before launching another
full-battle run.

Before submission, export the local evidence pack:

```bash
scripts/export_submission_pack.sh
```

The pack is written under `.runtime/submission-pack/` and includes the latest
summary, job JSON, rendered proof console HTML, tx links, rehearsal report when
available, manifest, and `SUBMISSION_NOTES.md`.

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

Latest verified full-battle run: `3beec5c8-3a95-4058-8962-9408fb951465` on
May 2, 2026. It completed in `773s`, produced 7 chain receipts, validated the
risk REE receipt, and indexed `tasks=9`, `contributions=23`,
`verifications=0`, `reputation=23`.

Latest exported evidence pack:

```text
.runtime/submission-pack/20260502_125554
```

Current walkthrough URL:

```text
http://127.0.0.1:8004
```

Current verification bundle:

```text
http://127.0.0.1:8004/jobs/3beec5c8-3a95-4058-8962-9408fb951465/verify
```

Use the REE E2E script when recording reproducible inference evidence:

```bash
REE_SH=/tmp/gensyn-ree/ree.sh REE_CPU_ONLY=1 .venv/bin/python scripts/verify_ree_e2e.py
```

## Claims to Make

- Signal Count is a proof console for AI analyst work: the memo is useful, but
  the differentiator is that each agent contribution can be traced.
- Signal Count routes specialist work through AXL and records per-role dispatch
  evidence.
- Signal Count produces verifier-scored specialist evidence, output hashes, and
  a source-linked memo. Current demo market/news inputs are explicitly
  fixture-labelled unless a live adapter is added.
- Signal Count exposes a structured verification bundle for stored run evidence
  through `GET /jobs/{job_id}/verify`.
- Signal Count can attach real Gensyn REE receipt metadata to the risk
  specialist path when REE is enabled.
- Signal Count uses `risk-only-ree` as the active REE policy; when REE is
  enabled, the verifier rejects risk output that lacks required REE evidence.
- Signal Count surfaces risk REE proof details together: model, prompt hash,
  token hash, receipt hash, output hash, and contribution tx when available.
- Signal Count records peer selection reason for each specialist dispatch.
- Signal Count can record and display Gensyn Testnet task, contribution, and
  reputation receipts when chain writing is configured.
- Signal Count can rebuild chain-backed projections from indexed contract
  events after restart.
- Signal Count includes a proof-console UI that shows capability state, mesh
  visualization, run timeline, final memo, task trace, REE status, explorer
  links, reputation evidence, and indexed event counts.

## Claims to Avoid

- Do not claim event-level semantic reconstruction or archival/reorg chain
  verification beyond RPC transaction receipt status.
- Do not claim autonomous peer-market routing. The implemented routing is
  topology/capability-based over configured candidate peers.
- Do not claim all inference is REE-backed unless `all-llm-ree` is configured
  and every relevant specialist output is backed by REE evidence.
- Do not claim remote multi-machine AXL execution unless the demo actually runs
  across separate hosts.
- Do not claim ERC20, USDC, stablecoin, or real-money rewards.
- Do not claim native test-ETH payout as anything beyond tiny capped testnet
  evidence.
- Do not claim full archival chain reorg rollback beyond the configured repair
  window.
- Do not describe offline preview fixtures as live AXL, REE, or Gensyn Testnet
  evidence.
- Do not describe fixture market/news inputs as live retrieval.

## Closed Submission Scope

- Direct full-battle execution, format pass, and fast prewarmed demo.
- User-triggered verification bundle and UI controls.
- Explicit REE policy with precise `present` / `parsed` / `validated` /
  `verified` language.
- AXL peer selection and fallback based on configured candidate peers, topology
  health, and verifier/reputation metadata when available.
- Source-backed or fixture-labelled evidence inputs.
- First screen shows completed proof console, not a blank intake form.
