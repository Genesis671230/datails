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
(10 Jul 2026), including the founder-approved `POST /api/v1/learning-events`
ingestion route. 106 tests at slice close. Details:
`docs/build-log/2026-07-10-slice-2.md`.
Remaining: swap mock → live Foundry after LD-23/24 verification; golden set
re-runs unchanged.

**Slice 3 — Trace loop + deploy**: trace loop complete on fixtures
(10 Jul 2026): FIFO engine, trace routes, LD-27 state machine with
interrupt/resume, explorer graph, named case-memory test. 117 tests green.
Details: `docs/build-log/2026-07-10-slice-3.md`.
Remaining: the deploy half (Bicep completion, OIDC pipeline, rollback drill)
and the loop run in Azure on the real AQ dataset — blocked on prerequisites.

## Azure stamp (deployed 10 Jul 2026)

Resource group `datails-dev` in **swedencentral** (LD-23 twice-amended — see
DECISIONS.md): Key Vault (`datails-dev-kv`, holds `postgres-admin-password`),
Storage `datailsdevsnap` (soft-delete 30d + versioning), Postgres 16
`datails-dev-pg` (14-day PITR, Ready), Container Apps env, App Insights +
Log Analytics, budget alert → insights@datails.ai. Foundry
`datails-dev-foundry` with deployments `gpt-5-4` (100K TPM) and `gpt-5-mini`
(150K TPM), DataZoneStandard (LD-24 amended — GPT-4o family undeployable).
GitHub OIDC: app `datails-github-deploy` federated to
`repo:datailstech/datails:ref:refs/heads/main`, Contributor on the RG; repo
secrets AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID set.

## Open blockers (founder prerequisites)

- **Entra External ID tenant** (LD-1): portal-only creation — steps in the
  Azure section of the Slice 3 build log; app registrations follow via CLI.
- **Crystal temporary key** (LD-22) → LD-6 spike → live Slice 1 acceptance.
- **Anonymised AQ dataset** → replaces the placeholder fixture.
- Remaining Slice 3 deploy work now unblocked: AzureFoundryClient behind the
  ModelClient interface, container deploy to ACA, deploy workflow, rollback
  drill.

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
