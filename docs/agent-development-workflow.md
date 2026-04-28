# Signal Count Agent Development Workflow

This document is the working reference for future AI agents developing Signal
Count. It translates the strategic roadmap into phase gates, task blocks,
review rules, and comparison checkpoints.

Use this before changing code. The goal is to evolve Signal Count from an
AXL-routed demo into a verifiable analyst swarm:

```text
AXL dispatch
  -> signed specialist output
  -> REE receipt
  -> Gensyn Testnet receipt
  -> verifier attestation
  -> final memo
```

## Source Practices

This workflow adapts governance practices from:

- `https://github.com/ashishki/AI_workflow_playbook`
- `https://docs.gensyn.ai/tech`
- `https://docs.gensyn.ai/tech/ree/receipts`
- `https://docs.gensyn.ai/testnet`

Adopted practices:

- File-based state is preferred over conversational memory.
- Phases require explicit gates before advancement.
- Implementation and review responsibilities must stay separated.
- Every task must have a declared owner, type, file scope, and acceptance
  criteria.
- Tests and demo evidence are part of task completion, not polish.
- Riskier capability areas require stronger review and evidence.

## Agent Operating Rules

1. Read this document, `docs/ARCHITECTURE.md`, `docs/spec.md`, and
   `docs/development-plan.md` before implementation.
2. Do not start from the most complex architecture. Compare the requested work
   against the phase target and implement the smallest change that advances the
   current phase.
3. Do not weaken the existing AXL proof path. Live mode must not silently fall
   back to offline preview.
4. Do not claim remote multi-machine execution unless it is actually verified.
5. Do not claim REE verification unless a real REE receipt was generated and
   validated or verified.
6. Do not claim on-chain receipts unless a Gensyn Testnet transaction hash is
   persisted and visible in the explorer.
7. Every new boundary must have a schema, tests, and failure behavior.
8. Every phase must preserve or improve the current test baseline.

## Current Baseline

Current system shape:

```text
FastAPI UI/API
  -> CoordinatorService
  -> AXLClient
  -> AXL MCP route /mcp/{peer_id}/{service_name}
  -> regime / narrative / risk nodes
  -> MemoSynthesisService
  -> SQLite JobStore
  -> local provenance ledger
```

Known strengths:

- AXL local bridge path exists.
- Multi-peer same-machine AXL mesh scripts exist.
- Specialist execution records include role, peer, service, transport, status,
  latency, and dispatch target.
- Partial failure is explicit.
- Tests cover API, coordinator, AXL client, nodes, rendering, and failure paths.

Known gaps:

- No cryptographic agent signatures.
- No REE-backed inference receipts.
- No Gensyn Testnet contract receipts.
- No verifier node.
- No reputation or reward accounting.
- No event indexer.
- UI does not yet expose a live trace graph or explorer-backed evidence.

## Capability Profile Decisions

| Profile | Status | Applies To | Required Artifact |
| --- | --- | --- | --- |
| Tool-Use | ON | AXL transport, chain writes, REE CLI, explorer/indexer calls | Tool schemas and side-effect gates in task AC |
| Agentic | ON, bounded | Specialist agents and verifier agent | Termination and authority boundaries per role |
| Planning | ON, workflow-only | Development and task graph planning | This document and structured task blocks |
| RAG | OFF for now | No managed corpus exists yet | Revisit only if real evidence corpus is added |
| Compliance | OFF for now | No regulated data scope | Revisit if user data, trading, or custody grows |

Runtime tier:

| Subsystem | Tier | Rationale |
| --- | --- | --- |
| FastAPI app | T0/T1 | Normal service runtime |
| AXL nodes | T1 | Bounded worker services |
| REE runner | T1 | Containerized reproducible inference pipeline |
| Chain writer | T0/T1 | Managed RPC side effects with signing controls |
| Future autonomous workers | T2 only if they mutate workspace/toolchain |

## Phase Comparison Method

Before each implementation task, compare:

| Question | Required Answer |
| --- | --- |
| Which phase is active? | Name one phase from this document. |
| What is already implemented? | Cite local files or tests. |
| What target capability is missing? | Name the missing contract, module, UI state, or test. |
| What is the smallest safe change? | Declare concrete file scope. |
| What evidence proves completion? | Test, command, explorer tx, REE receipt, or screenshot. |

If the answer requires a capability from a later phase, either defer it or record
an explicit cross-phase dependency.

## Phase 0: Baseline Lock

Goal: establish the development floor before adding cryptographic or on-chain
layers.

Tasks:

```yaml
Task: T0-01
Owner: implementation-agent
Phase: 0
Type: workflow:baseline
Depends-On: []
Objective: Record the current test/lint baseline and known demo modes.
Acceptance-Criteria:
  - id: AC-T0-01-01
    description: Full local test command is documented with result count.
    test: python -m pytest tests/ -q --tb=short
  - id: AC-T0-01-02
    description: Ruff commands are documented with pass/fail result.
    test: ruff check app tests && ruff format --check app tests
Files:
  - docs/development-plan.md
  - docs/review-log.md
Notes: Do not change app behavior in this task.
```

Gate:

- Tests are not lower than the recorded baseline.
- Existing offline and AXL demo scripts remain documented.

## Phase 1: Canonical Hashing and Agent Identity

Goal: make every task and agent response hashable, signable, and attributable.

Target architecture delta:

```text
SpecialistResponse
  -> canonical JSON
  -> output_hash
  -> agent wallet signature
  -> recoverable signer
```

New modules:

```text
app/identity/
  canonical.py
  hashing.py
  signing.py
```

Schema additions:

- `TaskSpec`
- `AgentIdentity`
- `SignedAgentExecution`
- `SignatureEnvelope`

Tasks:

```yaml
Task: T1-01
Owner: implementation-agent
Phase: 1
Type: identity:canonical
Depends-On: [T0-01]
Objective: Add deterministic canonical JSON and keccak hashing helpers.
Acceptance-Criteria:
  - id: AC-T1-01-01
    description: Equivalent dictionaries produce the same canonical bytes.
    test: tests/test_identity_canonical.py::test_canonical_json_is_order_stable
  - id: AC-T1-01-02
    description: Hash helper returns stable hex digest for known fixture.
    test: tests/test_identity_canonical.py::test_keccak_hash_matches_fixture
Files:
  - app/identity/canonical.py
  - app/identity/hashing.py
  - tests/test_identity_canonical.py
```

```yaml
Task: T1-02
Owner: implementation-agent
Phase: 1
Type: identity:signing
Depends-On: [T1-01]
Objective: Sign and recover specialist execution envelopes.
Acceptance-Criteria:
  - id: AC-T1-02-01
    description: A signed response recovers the expected wallet address.
    test: tests/test_identity_signing.py::test_signed_execution_recovers_signer
  - id: AC-T1-02-02
    description: Tampered payload fails signature verification.
    test: tests/test_identity_signing.py::test_tampered_execution_fails_verification
Files:
  - app/identity/signing.py
  - app/schemas/contracts.py
  - tests/test_identity_signing.py
```

Gate:

- Every specialist response can be mapped to `role`, `peer_id`, `wallet`,
  `output_hash`, and `signature`.
- No chain or REE work begins before this gate passes.

Review focus:

- Canonicalization must not depend on Python dict insertion order.
- Signatures must bind task hash and output hash, not only display text.
- Private keys must come from env/config, never from committed files.

## Phase 2: Gensyn Testnet Contracts

Goal: create minimal on-chain primitives for agent registration, task creation,
contribution receipts, verifier attestations, and final memo receipts.

Target contracts:

```text
contracts/src/
  SignalAgentRegistry.sol
  SignalTaskRegistry.sol
  SignalReceiptRegistry.sol
  SignalReputationVault.sol
```

Minimum events:

- `AgentRegistered(address agent, bytes32 peerIdHash, string role, string metadataURI)`
- `TaskCreated(uint256 taskId, bytes32 taskHash, string metadataURI)`
- `ContributionRecorded(uint256 taskId, address agent, string role, bytes32 outputHash, bytes32 reeReceiptHash, string metadataURI)`
- `VerificationRecorded(uint256 taskId, address verifier, bytes32 verdictHash, uint256 score)`
- `TaskFinalized(uint256 taskId, bytes32 memoHash)`

Tasks:

```yaml
Task: T2-01
Owner: implementation-agent
Phase: 2
Type: chain:contracts
Depends-On: [T1-02]
Objective: Implement and test minimal registry/receipt contracts locally.
Acceptance-Criteria:
  - id: AC-T2-01-01
    description: Agent registration emits AgentRegistered.
    test: forge test --match-test testRegisterAgent
  - id: AC-T2-01-02
    description: Task and contribution recording emit expected events.
    test: forge test --match-test testRecordContribution
Files:
  - contracts/src/SignalAgentRegistry.sol
  - contracts/src/SignalTaskRegistry.sol
  - contracts/src/SignalReceiptRegistry.sol
  - contracts/test/
```

```yaml
Task: T2-02
Owner: implementation-agent
Phase: 2
Type: chain:deployment
Depends-On: [T2-01]
Objective: Deploy contracts to Gensyn Testnet and record addresses.
Acceptance-Criteria:
  - id: AC-T2-02-01
    description: Deployment script targets chain ID 685685.
    test: forge script script/DeployGensynTestnet.s.sol --rpc-url $GENSYN_RPC_URL --broadcast
  - id: AC-T2-02-02
    description: Contract addresses and explorer links are documented.
    test: manual explorer verification
Files:
  - contracts/script/DeployGensynTestnet.s.sol
  - docs/gensyn-contracts.md
```

Gate:

- Contract addresses are documented.
- At least one explorer transaction proves deployment.
- Backend integration does not start until ABI/address files are stable.

Review focus:

- Events must contain enough data for UI/indexer reconstruction.
- Contracts should store hashes and references, not large memo text.
- Reward logic should not block receipt recording.

## Phase 3: Chain Integration Layer

Goal: connect the FastAPI backend to deployed Gensyn Testnet contracts.

New modules:

```text
app/chain/
  config.py
  client.py
  receipts.py
  explorer.py
```

New settings:

- `GENSYN_RPC_URL`
- `GENSYN_CHAIN_ID=685685`
- `GENSYN_EXPLORER_BASE_URL=https://gensyn-testnet.explorer.alchemy.com`
- `SIGNAL_AGENT_REGISTRY_ADDRESS`
- `SIGNAL_TASK_REGISTRY_ADDRESS`
- `SIGNAL_RECEIPT_REGISTRY_ADDRESS`
- `CHAIN_WRITER_PRIVATE_KEY`

Tasks:

```yaml
Task: T3-01
Owner: implementation-agent
Phase: 3
Type: chain:client
Depends-On: [T2-02]
Objective: Add contract client wrappers for task and contribution writes.
Acceptance-Criteria:
  - id: AC-T3-01-01
    description: Client builds and signs a createTask transaction.
    test: tests/test_chain_client.py::test_build_create_task_transaction
  - id: AC-T3-01-02
    description: Explorer URL helper renders expected transaction URL.
    test: tests/test_chain_client.py::test_explorer_tx_url
Files:
  - app/chain/
  - app/config/settings.py
  - tests/test_chain_client.py
```

```yaml
Task: T3-02
Owner: implementation-agent
Phase: 3
Type: chain:receipts
Depends-On: [T3-01]
Objective: Persist task, contribution, verification, and finalization tx hashes.
Acceptance-Criteria:
  - id: AC-T3-02-01
    description: Job record stores per-role contribution tx hashes.
    test: tests/test_jobs_api.py::test_job_persists_chain_receipts
  - id: AC-T3-02-02
    description: Chain failure marks receipt_status=failed without hiding memo output.
    test: tests/test_chain_receipts.py::test_chain_failure_degrades_explicitly
Files:
  - app/store/jobs.py
  - app/api/jobs.py
  - app/coordinator/service.py
  - tests/test_chain_receipts.py
```

Gate:

- One completed live job records explorer links for task and contributions.
- If chain writes fail, UI shows failed/pending receipt status explicitly.
- Offline preview must not display fake explorer links.

Review focus:

- Chain side effects must be idempotent or retry-safe.
- Transaction failures must not corrupt completed local job state.
- Private key and RPC errors must not leak secrets.

## Phase 4: REE Integration

Goal: back at least one specialist output with a real Gensyn REE receipt.

Start with the `risk` role because adversarial critique is easiest to explain
and verify during the demo.

New modules:

```text
app/ree/
  config.py
  runner.py
  receipts.py
  validator.py
```

Target flow:

```text
Risk payload
  -> prompt JSONL or prompt text
  -> gensyn-sdk run --operation-set reproducible
  -> receipt JSON
  -> receipt_hash
  -> SpecialistResponse.ree_receipt_hash
  -> on-chain ContributionRecorded
```

Tasks:

```yaml
Task: T4-01
Owner: implementation-agent
Phase: 4
Type: ree:adapter
Depends-On: [T1-02]
Objective: Add REE receipt parser and validator for local receipt files.
Acceptance-Criteria:
  - id: AC-T4-01-01
    description: Parser extracts model, prompt_hash, parameters_hash, tokens_hash, receipt_hash, and text_output.
    test: tests/test_ree_receipts.py::test_parse_ree_receipt_fixture
  - id: AC-T4-01-02
    description: Validator detects receipt_hash mismatch in fixture.
    test: tests/test_ree_receipts.py::test_invalid_ree_receipt_fails_validation
Files:
  - app/ree/receipts.py
  - app/ree/validator.py
  - tests/fixtures/ree/
  - tests/test_ree_receipts.py
```

```yaml
Task: T4-02
Owner: implementation-agent
Phase: 4
Type: ree:runner
Depends-On: [T4-01]
Objective: Add optional REE runner for selected specialist roles.
Acceptance-Criteria:
  - id: AC-T4-02-01
    description: REE runner builds deterministic command args without shell injection.
    test: tests/test_ree_runner.py::test_ree_runner_builds_safe_args
  - id: AC-T4-02-02
    description: Risk service can use REE text output when REE is enabled.
    test: tests/test_risk_service.py::test_risk_service_uses_ree_output_when_enabled
Files:
  - app/ree/runner.py
  - app/nodes/risk/service.py
  - app/config/settings.py
  - tests/test_ree_runner.py
```

Gate:

- At least one real REE receipt is generated outside unit tests.
- Receipt validation result is shown in UI.
- The on-chain contribution includes `reeReceiptHash`.

Review focus:

- Do not mark a receipt as verified if only local validation ran.
- Distinguish `receipt_validated` from `receipt_verified`.
- REE subprocess arguments must be list-based, not string-concatenated shell.

## Phase 5: Verifier Agent and Evaluation

Goal: add an explicit verifier role that scores specialist outputs before final
memo synthesis.

New modules:

```text
app/nodes/verifier/
  service.py
app/evaluation/
  scoring.py
  attestations.py
```

Verifier dimensions:

| Dimension | Weight |
| --- | ---: |
| Schema validity | 0.20 |
| Task relevance | 0.20 |
| Evidence specificity | 0.20 |
| Dissent value | 0.15 |
| Receipt strength | 0.15 |
| Latency / completion | 0.10 |

Tasks:

```yaml
Task: T5-01
Owner: implementation-agent
Phase: 5
Type: evaluation:verifier
Depends-On: [T1-02, T3-02]
Objective: Add verifier service that scores signed specialist executions.
Acceptance-Criteria:
  - id: AC-T5-01-01
    description: Valid signed outputs receive nonzero verifier score.
    test: tests/test_verifier_service.py::test_verifier_scores_valid_execution
  - id: AC-T5-01-02
    description: Invalid signatures are rejected.
    test: tests/test_verifier_service.py::test_verifier_rejects_invalid_signature
Files:
  - app/nodes/verifier/service.py
  - app/evaluation/scoring.py
  - tests/test_verifier_service.py
```

```yaml
Task: T5-02
Owner: implementation-agent
Phase: 5
Type: orchestration:graph
Depends-On: [T5-01]
Objective: Run verifier after specialists and before memo synthesis.
Acceptance-Criteria:
  - id: AC-T5-02-01
    description: Coordinator waits for verifier before synthesis.
    test: tests/test_coordinator_service.py::test_verifier_runs_before_synthesis
  - id: AC-T5-02-02
    description: Rejected specialist output is excluded or marked rejected in memo provenance.
    test: tests/test_memo_synthesis.py::test_rejected_specialist_output_is_visible
Files:
  - app/coordinator/service.py
  - app/coordinator/synthesis.py
  - app/schemas/contracts.py
```

Gate:

- Final memo differentiates accepted, rejected, and missing contributions.
- Verification attestation is signed and optionally recorded on-chain.

Review focus:

- Verifier must not silently rewrite specialist claims.
- Rejection must be visible to users.
- Evaluation rules must be deterministic where possible.

## Phase 6: Task Graph Orchestration

Goal: replace hardcoded three-role fan-out with a declared workflow graph.

New modules:

```text
app/orchestration/
  graph.py
  executor.py
  state.py
```

Target graph:

```json
{
  "nodes": [
    {"id": "regime", "type": "specialist"},
    {"id": "narrative", "type": "specialist"},
    {"id": "risk", "type": "specialist"},
    {"id": "verifier", "type": "verifier"},
    {"id": "synthesis", "type": "coordinator"}
  ],
  "edges": [
    ["regime", "verifier"],
    ["narrative", "verifier"],
    ["risk", "verifier"],
    ["verifier", "synthesis"]
  ]
}
```

Tasks:

```yaml
Task: T6-01
Owner: implementation-agent
Phase: 6
Type: orchestration:graph
Depends-On: [T5-02]
Objective: Introduce graph-defined execution without changing external API.
Acceptance-Criteria:
  - id: AC-T6-01-01
    description: Default graph reproduces current regime/narrative/risk behavior.
    test: tests/test_orchestration_graph.py::test_default_graph_matches_existing_roles
  - id: AC-T6-01-02
    description: Missing optional node produces partial graph state, not total failure.
    test: tests/test_orchestration_graph.py::test_optional_node_failure_is_partial
Files:
  - app/orchestration/
  - app/coordinator/service.py
  - tests/test_orchestration_graph.py
```

Gate:

- Existing `/jobs` contract remains compatible.
- UI can show graph state per node.
- Partial failure semantics are preserved.

Review focus:

- Do not add open-ended autonomous loops.
- Graph must have explicit termination.
- Role authority boundaries must remain fixed.

## Phase 7: Reputation and Rewards

Goal: make agent incentives visible without overclaiming real monetary payout.

Initial implementation:

- Reputation points only.
- Optional capped native test-ETH micro-payout, disabled by default.
- Optional mock ERC20/test token later.
- No real USDC claims unless actual supported infrastructure exists.

Tasks:

```yaml
Task: T7-01
Owner: implementation-agent
Phase: 7
Type: incentives:reputation
Depends-On: [T5-02]
Objective: Add deterministic reputation updates from verifier scores.
Acceptance-Criteria:
  - id: AC-T7-01-01
    description: Valid contribution increases role-specific reputation.
    test: tests/test_reputation.py::test_valid_contribution_increases_reputation
  - id: AC-T7-01-02
    description: Invalid contribution does not receive reward credit.
    test: tests/test_reputation.py::test_invalid_contribution_gets_no_credit
Files:
  - app/evaluation/reputation.py
  - app/store/jobs.py
  - tests/test_reputation.py
```

```yaml
Task: T7-02
Owner: implementation-agent
Phase: 7
Type: incentives:onchain
Depends-On: [T7-01, T2-02]
Objective: Record reputation/reward updates on-chain.
Acceptance-Criteria:
  - id: AC-T7-02-01
    description: Reputation update emits event with agent, role, score, and taskId.
    test: forge test --match-test testRecordReputation
Files:
  - contracts/src/SignalReputationVault.sol
  - app/chain/receipts.py
```

Gate:

- Leaderboard can be reconstructed from events or local projection.
- Rewards are labelled as reputation/test rewards unless capped test-ETH or real
  token support is implemented and verified.

Review focus:

- No hidden manual reward edits.
- No reward without verifier score.
- No monetary language unsupported by chain evidence.
- If native test ETH is used, payout amounts must be tiny fractions of ETH with a
  hard per-run cap so test balances are not drained.

## Phase 8: UI and Demo Productization

Goal: make AXL, REE, and on-chain proof legible in the product.

Required screens:

- Command Console
- Agent Registry
- Task Trace
- Memo Artifact
- Receipts and Explorer
- Reputation Leaderboard

UI evidence model:

```text
claim text
  -> source role
  -> agent wallet
  -> AXL peer ID
  -> output_hash
  -> REE receipt hash, if present
  -> contribution tx hash
```

Tasks:

```yaml
Task: T8-01
Owner: implementation-agent
Phase: 8
Type: ui:trace
Depends-On: [T3-02]
Objective: Redesign run evidence as a trace ledger with explorer links.
Acceptance-Criteria:
  - id: AC-T8-01-01
    description: Each contribution row shows role, peer, wallet, output hash, receipt status, and tx link.
    test: tests/test_demo_ui.py::test_trace_ledger_renders_receipts
Files:
  - app/api/pages.py
  - app/templates/index.html
  - tests/test_demo_ui.py
```

```yaml
Task: T8-02
Owner: implementation-agent
Phase: 8
Type: ui:memo
Depends-On: [T5-02]
Objective: Link memo bullets to accepted specialist contributions.
Acceptance-Criteria:
  - id: AC-T8-02-01
    description: Memo HTML exposes source role and hash for each evidence item.
    test: tests/test_rendering.py::test_memo_evidence_renders_source_hash
Files:
  - app/rendering/memo.py
  - app/schemas/contracts.py
  - tests/test_rendering.py
```

Gate:

- A judge can understand the full proof path from the UI alone.
- Offline demo clearly labels fake/preset evidence.
- Live demo shows explorer-backed rows.

Review focus:

- Visual polish must not obscure proof states.
- Pending/failed/confirmed states must be visually distinct.
- Do not invent receipt data in demo fixtures.

## Phase 9: Event Indexer and Recovery

Goal: make the UI and backend recoverable from chain events plus local receipt
metadata.

New modules:

```text
app/indexer/
  chain_events.py
  projections.py
```

Tasks:

```yaml
Task: T9-01
Owner: implementation-agent
Phase: 9
Type: indexing:events
Depends-On: [T3-02]
Objective: Poll contract events into local projections.
Acceptance-Criteria:
  - id: AC-T9-01-01
    description: Indexer stores task, contribution, verification, and finalization events.
    test: tests/test_indexer.py::test_indexer_projects_receipt_events
Files:
  - app/indexer/
  - app/store/jobs.py
  - tests/test_indexer.py
```

Gate:

- Restarting the app does not lose visible receipt state.
- Projection can rebuild agent leaderboard from events.

Review focus:

- Indexer must handle duplicate events idempotently.
- Reorg assumptions must be documented.
- Local DB must distinguish indexed chain facts from local-only metadata.

## Phase 10: Proof Console UX

Goal: turn the existing demo page into a trustworthy operator console where a
judge can understand the proof path without reading raw JSON.

Design direction:

- Build an operational dashboard, not a marketing landing page.
- Put proof state above decoration: mode, status, peer, wallet, hash, receipt,
  tx, and memo source should be visible and scannable.
- Use restrained colors: green only for accepted/confirmed, red only for
  failed/rejected, amber for parsed/pending, and monospace chips for hashes.
- Keep offline, live AXL, REE, and chain states visually distinct.

Required surfaces:

- Command Console
- Mode and Capability Strip
- Agent Registry / Mesh Panel
- Run Timeline
- Task Trace Ledger
- Memo Artifact
- Proof Drawer
- Reputation / Indexed Events Panel

Tasks:

```yaml
Task: T10-01
Owner: implementation-agent
Phase: 10
Type: ui:layout
Depends-On: [T8-01, T8-02, T9-01]
Objective: Redesign the home page as a proof-first operator console.
Acceptance-Criteria:
  - id: AC-T10-01-01
    description: Home page renders command console, capability strip, run timeline, task trace, memo, and reputation/indexed-event panels.
    test: tests/test_demo_ui.py::test_home_page_renders_proof_console_layout
Files:
  - app/api/pages.py
  - app/templates/index.html
  - tests/test_demo_ui.py
```

```yaml
Task: T10-02
Owner: implementation-agent
Phase: 10
Type: ui:proof
Depends-On: [T5-02, T8-01]
Objective: Add a proof drawer/detail view for hashes, signatures, receipts, and explorer links.
Acceptance-Criteria:
  - id: AC-T10-02-01
    description: Proof details expose full output hash, attestation hash, verifier signature, REE receipt hash/status, and tx link when available.
    test: tests/test_demo_ui.py::test_proof_details_render_full_receipt_metadata
Files:
  - app/api/pages.py
  - app/templates/index.html
  - tests/test_demo_ui.py
```

```yaml
Task: T10-03
Owner: implementation-agent
Phase: 10
Type: ui:responsive
Depends-On: [T10-01]
Objective: Make the proof console readable on laptop and mobile-width screenshots.
Acceptance-Criteria:
  - id: AC-T10-03-01
    description: Long peer IDs, hashes, and tx links do not overlap or overflow core panels.
    test: tests/test_demo_ui.py::test_proof_console_wraps_long_identifiers
Files:
  - app/templates/index.html
  - tests/test_demo_ui.py
```

Gate:

- A judge can explain the proof path from the first completed run screen.
- The UI never visually upgrades missing proof into confirmed proof.
- Offline preview remains clearly labelled as offline.
- Long hashes, peer IDs, and tx links remain readable without layout overlap.
- The memo remains the main artifact; proof panels support it rather than hiding
  it.

Review focus:

- Visual polish must not obscure proof states.
- Operational density should improve clarity, not create a wall of tables.
- UI copy must avoid unsupported claims about remote deployment, REE, rewards,
  or chain receipts.
- Screenshots must be readable at typical hackathon submission thumbnail size.

## Phase Gate Checklist

Every phase gate must answer:

- What changed architecturally?
- Which files were modified?
- Which tests prove the change?
- What demo evidence exists?
- What remains local-only?
- What is cryptographically signed?
- What is backed by REE?
- What is backed by Gensyn Testnet explorer evidence?
- What claims must not be made yet?

## Light Review Checklist

Run after each task:

- Schema compatibility is preserved or explicitly migrated.
- Tests cover success and failure path.
- No secrets are committed.
- Live mode does not silently use offline fallback.
- Side effects are idempotent or failure-visible.
- User-facing proof labels are truthful.

## Deep Review Checklist

Run at phase boundaries:

- Architecture drift: Does implementation still match target phase?
- Proof integrity: Are hashes, signatures, REE receipts, and tx hashes correctly
  bound to the same task?
- Gensyn-native fit: Does this phase strengthen AXL, REE, or Testnet usage?
- UX clarity: Can a judge understand the proof path without reading code?
- Risk containment: Are private keys, RPC failures, subprocess calls, and chain
  writes handled safely?
- Scope control: Did the phase add speculative complexity without evidence?

## Deep Review Template

At each phase boundary, append a deep review entry to `docs/review-log.md`.
This is a review artifact, not a commit summary. It must be specific enough for
a different agent to resume from files alone.

Use this exact structure:

```markdown
## Phase N Deep Review — <Phase Name>

Date: YYYY-MM-DD
Reviewer: implementation-agent self-check before human phase approval
Baseline:
- Tests:
- Lint:
- Format:

### Phase Scope

- Planned phase:
- Completed tasks:
- Deferred tasks:
- Explicitly not started:

### Files Changed

- `path/to/file`: reason

### Architecture Drift

Decision: PASS | FAIL

Evidence:
- ...

Questions:
- ...

### Proof Integrity

Decision: PASS | FAIL

Evidence:
- Hashes/signatures/receipts/tx links are bound to:
- Local-only evidence is labelled:
- Mock/demo evidence is labelled:

Questions:
- ...

### Gensyn-Native Fit

Decision: PASS | FAIL

Evidence:
- AXL:
- REE:
- Gensyn Testnet:

Questions:
- ...

### UX / Operator Clarity

Decision: PASS | FAIL | NOT_APPLICABLE

Evidence:
- ...

Questions:
- ...

### Risk Containment

Decision: PASS | FAIL

Evidence:
- Secrets:
- Side effects:
- Failure modes:
- Idempotency/retry behavior:

Questions:
- ...

### Scope Control

Decision: PASS | FAIL

Evidence:
- Work stayed within phase:
- Later-phase work avoided:
- Any cross-phase dependency:

Questions:
- ...

### Findings

P0:
- None | finding

P1:
- None | finding

P2:
- None | finding

P3:
- None | finding

### Gate Decision

Decision: READY | BLOCKED

Rationale:
- ...

Next allowed action:
- ...
```

Deep review rules:

- `READY` is forbidden if any P0 or P1 remains unresolved.
- A `FAIL` in Architecture Drift, Proof Integrity, Gensyn-Native Fit, Risk
  Containment, or Scope Control requires `BLOCKED` unless the section is
  explicitly `NOT_APPLICABLE` for the phase.
- Do not mark REE as present unless a real REE receipt exists.
- Do not mark Gensyn Testnet as present unless a real transaction hash exists.
- Do not mark proof as cryptographic unless hashes/signatures are actually
  produced and verified by tests.
- Human approval is required before starting the next phase after a `READY`
  gate.

## Stop Conditions

Stop implementation and ask for human approval if:

- A task requires changing a contract interface after deployment.
- A task needs real token or stablecoin semantics.
- A task would remove AXL from the live path.
- A task would replace real chain/REE evidence with mocked proof in live mode.
- Test baseline decreases.
- Private key handling is unclear.
- Gensyn documentation contradicts an intended claim.

## Final Target Demo

The final demo should show:

1. Registered agents with wallet, AXL peer ID, role, model, and reputation.
2. A thesis task created with a canonical task hash.
3. Specialist execution through AXL.
4. Signed specialist outputs.
5. At least one REE receipt generated and validated.
6. Gensyn Testnet contribution events with explorer links.
7. Verifier attestation and score.
8. Final memo with source-linked evidence.
9. Reputation update or test reward event.

The narrative:

```text
This is not an agent town. It is a proof layer for agent work:
distributed execution through AXL, reproducible inference through REE,
and public attribution through Gensyn Testnet receipts.
```
