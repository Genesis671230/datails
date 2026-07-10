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

**Slice 2 — AI layer**: **fully accepted, incl. live models** (10 Jul 2026).
Mock-backed build + founder-approved `POST /api/v1/learning-events`; then
AzureFoundryClient behind the ModelClient interface, and the golden set
passed against the live `gpt-5-4`/`gpt-5-mini` deployments in swedencentral
(substantive, `[ref:...]`-cited drafts; complete ai_call_log rows). CI stays
on the mock; the live golden run is repeatable via
`AI_BACKEND=azure_foundry` + `FOUNDRY_ENDPOINT` + `FOUNDRY_API_KEY` (Key
Vault secret `foundry-api-key`). Details:
`docs/build-log/2026-07-10-slice-2.md`.

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

## Entra External ID (LD-1, verified 10 Jul 2026)

Tenant `194ac953-cb8a-4e07-9890-65e73d2c024d` (`datails.onmicrosoft.com`,
created in Germany, EU data location). App registrations:
- **API** `Datails Backend API` — appId `00d8c4ff-db9c-4533-b344-48e08cf3af73`,
  scope `api://00d8c4ff-…/access_as_user`
- **SPA** `Datails Workspace (SPA)` — appId `01c24144-4b73-41df-b51d-592eb1e85785`,
  redirects `http://localhost:8765/callback`, `http://localhost:3000`;
  delegated: API scope + openid basics; admin-consented

Backend config (see `backend/scripts/run_backend_entra.sh`):
`ENTRA_AUTHORITY=https://<tenant-id>.ciamlogin.com/<tenant-id>/v2.0`
(= token issuer), `ENTRA_JWKS_URL=https://datails.ciamlogin.com/<tenant-id>/discovery/v2.0/keys`,
`ENTRA_AUDIENCE=<API appId>`.

**LD-26 PKCE real-token test: PASS** (`backend/scripts/pkce_login_test.py`):
genuine auth-code+PKCE flow as local customer account
`test.investigator@datails.onmicrosoft.com` → real token accepted by the
backend (bootstrap 200 creating tenant `pkce-test-tenant` with owner role;
me 200; tampered token 401). Frontend-relevant findings: workforce/admin
accounts cannot redeem CIAM tokens (AADSTS399266) — investigators must be
local accounts; SPA-platform code redemption requires a cross-origin
request (browser default; scripts need an Origin header).

## Open blockers (founder prerequisites)

- **Crystal temporary key** (LD-22) → LD-6 spike → live Slice 1 acceptance.
- **Anonymised AQ dataset** → replaces the placeholder fixture.
- Remaining Slice 3 deploy work, now fully unblocked: backend container
  deploy to ACA + deploy workflow over the OIDC federation, rollback drill,
  full loop in Azure.

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
