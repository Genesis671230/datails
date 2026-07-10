# Implementation Status

Last updated: 9 July 2026

## Completed slices

- **Slice 0 — Foundation** (9 Jul 2026): scaffold, full core schema (28
  tables, one migration, LD-3 insert-only enforcement), Entra JWT middleware
  (LD-1) + bootstrap/me, AQ methodology seed + placeholder AQ case fixture +
  synthetic Crystal fixtures, OpenAPI contract, Bicep skeleton, CI workflow.
  30 tests green. Details: `docs/build-log/2026-07-09-slice-0.md`.
- **Slice 1 — Case + Crystal ingestion** (9 Jul 2026): case domain routes
  (LD-8 detail shape), decisions with same-transaction ledger events (LD-9),
  ledger read endpoints (LD-8), connector registry + LD-4 execution pipeline,
  Crystal connector on replay fixtures (risk_check / full_investigation,
  LD-22), label provenance (LD-14), derived daily limits (LD-11) +
  shared-key budget (LD-22), idempotency middleware (LD-28), connector
  genericity enforced by tests (founder criterion). 72 tests green.
  **Open acceptance item:** live Crystal round-trip, gated on the temporary
  key + LD-6 spike. Details + key procedure:
  `docs/build-log/2026-07-09-slice-1.md`.

## Current slice

**Slice 2 — AI layer**: built and green on the deterministic mock backend
(10 Jul 2026): context builder (LD-5), model router + task executor (every
call logged), assistant endpoint (LD-20), reports draft/versions/approve
with jurisdiction overlays and LD-17 types, consent-gated learning capture
(LD-30), golden set (LD-29). 101 tests green. Details:
`docs/build-log/2026-07-10-slice-2.md`.

**Remaining for full Slice 2 acceptance:** swap the mock for the live
Foundry backend once LD-23/24 verification lands, re-run the golden set.

## Open blockers

- **LD-23/24 verification:** GPT-4o + GPT-4o-mini deployment availability and
  quota in West Europe — needs founder Azure/Foundry access. The mock carries
  everything else meanwhile.
- Live Crystal acceptance for Slice 1: waiting on the temporary key (LD-22);
  procedure in the Slice 1 build log.
- **Founder question (Slice 2 build log):** frontend-action learning events
  (assistant accept/reject, report edits) need an ingestion route not present
  in the canonical endpoint list — add `POST /api/v1/learning-events`, or
  defer to the frontend-contract work?

## Awaiting from founder (asked when a slice needs them)

- **Now (Slice 1 close-out):** Crystal temporary API key → `backend/.env`
  locally as `CRYSTAL_API_KEY` (Key Vault secret in Azure); triggers the
  LD-6 spike
- **Before Slice 2:** GPT-4o + GPT-4o-mini West Europe deployments verified,
  incl. quota (LD-23/24)
- **Slice 3:** Azure resource group (West Europe), Entra External ID app
  registration, GitHub repository OIDC federation (repo exists:
  `datailstech/datails`; local push needs `gh auth login`)
- **Anytime:** anonymised AQ case dataset (replaces placeholder fixture);
  cohort Data & Methodology Permission status per member (gates
  `learning_capture_enabled`, LD-30)

## Next milestone

Slice 2 acceptance: assistant returns a case-grounded, source-cited answer on
the AQ fixture; report draft cites sources; approval creates version + ledger
event; ai_call_log rows complete; learning_events only when the tenant flag
is true; golden set green.

## Post-pilot milestone: Connector Platform (BYO API + MCP)

**Do NOT build in Slices 1–3.**

Goal: investigators connect their own tools like any modern platform —
per-tenant API keys and MCP server connections behind the same connector
interface, ingestion pipeline (snapshot → hash → Data Ledger), and
provenance rules Crystal uses.

Scope:
- BYO API keys UX (`credential_owner=tenant`)
- Blockchain-explorer connector as connector #2
- `mcp_server` connector type implementation
- Connector registry/catalog surface

Sourced from BACKLOG items "MCP connectors" and "BYO connector keys UX"
(marked as promoted there). The Slice 1 connector-genericity criterion above
is the architectural down-payment on this milestone.
