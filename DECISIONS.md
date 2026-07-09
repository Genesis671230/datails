# Decisions

Architectural choices and their rationale. Locked decisions LD-1–LD-30 live in
`datails-spec/04_ERRATA_LOCKED_DECISIONS.md`; entries here record how they are
applied plus new deliberate choices made during the build.

## Pre-seeded at Slice 0 (required by the master prompt)

### No background workers in Phase 1 (LD-2)

Connector runs and AI tasks execute synchronously in the request path with
sensible timeouts. Deliberate pilot-scale decision; no `workers/` directory
until a real need arrives.

### Ledger hash chaining deferred (LD-3)

The ledgers (`data_ledger`, `decision_ledger`, `ai_call_log`,
`learning_events`) are insert-only at the database level (grants + triggers)
from their creating migration. Cross-entry hash chaining is deferred: per-entry
SHA-256 `payload_hash` plus DB-level immutability covers pilot-grade
provenance; chaining adds tamper-evidence across entries and can be layered on
later without schema change. Recorded in BACKLOG.

### Decisions table vs. Decision Ledger: source of truth (LD-9, verbatim)

`decisions` holds the current decision objects; `decision_ledger` is the
immutable event history. They are not alternatives — every decision write
emits a ledger event. Create/update/approve/supersede on a decision must, in
the same database transaction, append a `decision_ledger` event referencing
the `decision_id`. Decisions are never hard-deleted; a changed decision is
superseded by a new decision row plus a ledger event. Queries about "what is
decided now" read `decisions`. Queries about "how did we get here" read
`decision_ledger`.

### Crystal requires KYC of Datails end customers (LD-16)

Administrative obligation at tenant onboarding in the pilot (manual is
acceptable). Schema impact: none beyond a tenant metadata flag.

### Deferred integrations (05_DOMAIN_MODEL.md §4.3)

Codex portal (LE↔exchange comms) → USSS deconflict → CoinTracking/Blockpit
(tax vertical), in that evidence-backed order. Not Phase 1; recorded in
BACKLOG.

### Region: one pilot stamp in Azure West Europe (LD-23)

Founding cohort and their data subjects are European (court-facing story);
broader Foundry model availability. DIFC compliance attaches to Datails'
Dubai operations, not to hosting location. Region is a Bicep parameter;
a UAE North stamp is a later deployment of the same templates.

### Runtime: Azure Container Apps, not AKS (LD-25)

Days-to-live timeline; ACA revision-based rollback; the same containers move
to AKS later if enterprise deployment demands it. This deviates from the
signed sprint document's AKS Bicep (founder took over the build, 9 Jul 2026).

### Methodology versioning via integer column (LD-19)

`methodologies.version` is sufficient for Phase 1 — no `methodology_versions`
table.

## Slice 0 build decisions

### Two-role database model for LD-3

The runtime connects as `datails_app`; migrations run as `datails_owner`.
The migration that creates the ledger tables grants `datails_app`
INSERT+SELECT only and installs UPDATE/DELETE-rejecting triggers (defense in
depth against owner-role connections too). Locally the app role is provisioned
by `backend/db-init/01-app-role.sql`; in Azure by deployment tooling.

### Idempotency records successful responses only (Slice 1, LD-28)

Only 2xx responses are stored for replay. A failed outcome (missing
connector, upstream error) stays retryable under the same Idempotency-Key —
freezing an error response forever would defeat the retry purpose of the
mechanism. Replayed responses carry `X-Idempotent-Replay: true`. Response
payloads are stored via the blob backend; `idempotency_keys.response_ref`
holds the reference (05 §11 shape unchanged).

### Health endpoint reports liveness only

`/api/v1/health` (the only unauthenticated route, LD-1) does not gate on
database connectivity, so orchestrator restarts are reserved for process
death rather than transient dependency failures.
