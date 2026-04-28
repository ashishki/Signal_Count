# Product Specification — Signal Count

## Overview

Signal Count is a backend-first hackathon application that evaluates one market
thesis through specialist services routed via AXL. The system returns a
structured risk memo with scenarios, supporting evidence, opposing evidence,
counter-thesis, invalidation conditions, and provenance rather than a generic
conversational answer.

## User Roles

| Role | Capabilities |
| --- | --- |
| Operator | Submit a thesis, view job progress, inspect final memo, replay a demo thesis |
| Judge / viewer | Observe node participation, topology evidence, proof ledger, and final memo artifact |

## Feature Area 1 — Thesis Intake

Accept a single thesis request with asset and time horizon, validate the payload,
and normalize it into a bounded analysis job.

Acceptance criteria:

- The API accepts a thesis payload with `thesis`, `asset`, and `horizon_days`.
- Invalid requests receive structured validation errors.
- A valid request creates a job record with a stable `job_id`.
- The operator can see the normalized forecast question associated with the job.

Out of scope:

- User accounts.
- Batch thesis uploads.
- Multi-asset comparative jobs.

## Feature Area 2 — Distributed Specialist Analysis

Dispatch one job from the coordinator through the local AXL node to specialist
services on separate AXL peers and collect structured responses.

Acceptance criteria:

- The coordinator uses the local AXL bridge for specialist calls rather than
  direct specialist HTTP bypass.
- At least three specialist roles are supported: regime, narrative, and risk.
- Each specialist response includes `job_id`, `node_role`, `peer_id`, structured
  findings, and a timestamp.
- The operator can inspect topology and node participation evidence.
- Live local verification shows coordinator -> AXL bridge -> MCP router ->
  specialist `/mcp` services.
- Multi-peer local verification shows coordinator -> AXL node A -> AXL node B ->
  remote MCP router -> specialist `/mcp` services with distinct AXL public keys.

Out of scope:

- Dynamic service discovery.
- Reputation or marketplace pricing.
- Arbitrary third-party agent joining.
- Claiming remote multi-machine execution when the demo only runs a same-machine
  multi-peer mesh.

## Feature Area 3 — Memo Synthesis

Combine specialist outputs into a final memo that is useful for a fast decision
review and clearly separates support, opposition, and uncertainty.

Acceptance criteria:

- The final memo includes a normalized thesis, scenario table, key catalysts,
  top risks, and invalidation triggers.
- The final memo preserves specialist provenance by node role and peer ID.
- The system can render the memo as structured JSON and HTML.
- The final memo avoids generic chatbot formatting and uses fixed sections.

Out of scope:

- Personalized recommendations.
- Trading recommendations with position sizing.
- Long-form research reports.

## Feature Area 4 — Failure Handling and Observability

Make distributed execution understandable during the demo and degrade safely if
one specialist is unavailable.

Acceptance criteria:

- Per-node status and latency are recorded for each job.
- If one specialist fails or times out, the job still completes with an explicit
  partial-coverage warning.
- The system never silently substitutes a local fake specialist when a remote
  node is unavailable in live mode.
- `GET /health` returns `{"status": "ok"}` when the API is healthy.

Out of scope:

- Full monitoring dashboards.
- Complex retry queues.
- Production-grade SLO alerting.

## Feature Area 5 — Demo Operator View

Provide an operator screen that makes thesis input, node participation,
topology evidence, proof status, and final memo easy to understand.

Acceptance criteria:

- The operator can submit a thesis from a simple web form.
- The operator can see node-role participation, proof status, and final memo
  output in one place.
- A demo fixture can be replayed without depending on unstable live data.

Out of scope:

- Portfolio dashboarding.
- Decorative charts that do not explain the proof path.
- User management or saved portfolios.

## Feature Area 5A — Proof Console UX

Upgrade the demo operator view into a proof-first console for judges and
operators.

Acceptance criteria:

- The first completed-run screen shows command controls, current mode, proof
  capability state, mesh visualization, run timeline, task trace, final memo,
  and reputation/indexed event context.
- Agent rows show role, service, AXL peer ID, wallet, status, and reputation
  when available.
- Proof details expose full hashes, verifier signature metadata, REE receipt
  status, and explorer links without crowding the memo.
- Long peer IDs, hashes, and tx links wrap or truncate predictably without
  overlapping adjacent UI.
- Offline preview, live AXL, REE, chain receipt, and indexed-chain facts are
  labelled truthfully.
- The full battle script can produce readable terminal logs for video capture
  and a plain-text summary for evidence review.

Out of scope:

- Marketing landing page redesign.
- Decorative charts that do not improve proof comprehension.
- Hiding proof details behind unsupported claims or ambiguous badges.

## Feature Area 6 — Proof and Recovery Layer

Make the proof path inspectable without requiring judges to read raw JSON.

Acceptance criteria:

- Each completed run can expose AXL peer, wallet, output hash, verifier status,
  REE receipt status, and tx link metadata when available.
- Memo evidence bullets can be traced back to accepted specialist output hashes.
- Chain receipt events can be indexed into a local projection after restart.
- Duplicate event replay does not duplicate indexed facts.
- The indexer records failure status and repairs a configured shallow reorg
  window.

Out of scope:

- Claiming REE or Gensyn Testnet evidence for offline preview fixtures.
- Full archival reorg rollback beyond the configured repair window.
- ERC20, USDC, stablecoin, or real-money rewards.
