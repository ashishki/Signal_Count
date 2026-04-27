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
| Judge / viewer | Observe node participation, topology evidence, and final memo artifact |

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

Provide a minimal operator screen that makes thesis input, node participation,
topology evidence, and final memo easy to understand.

Acceptance criteria:

- The operator can submit a thesis from a simple web form.
- The operator can see node-role participation and final memo output in one
  place.
- A demo fixture can be replayed without depending on unstable live data.

Out of scope:

- Polished dashboarding.
- Rich charts.
- User management or saved portfolios.
