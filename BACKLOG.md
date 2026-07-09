# Backlog

Deferred items, each with a reason, appended at the moment of deferral
(LD-26). Nothing here blocks the pilot loop.

## Seeded at Slice 0 (per 07_BUILD_PLAN.md and LD-21)

| Item | Reason |
|---|---|
| Deterministic risk-rule engine | v7 item deferred by LD-21; not needed for the demonstrable loop |
| Entity registry (lite) | v7 item deferred by LD-21 |
| CrimeTrace ingestion endpoint | Separate build; this backend only exposes the case/evidence APIs it would feed |
| Credit backstop (HTTP 402) behavior | `tenants.credit_limit_usd` ships as schema hook only (LD-21) |
| Usage metering behavior (record writes + `GET /api/v1/usage/summary`) | Tables exist from Slice 0; metering behavior deferred per 07 |
| Methodology CRUD routes | Seed data only in pilot (07 deferrals) |
| UAE North stamp | Pilot is one West Europe stamp (LD-23); same templates redeploy later |
| MCP connectors | `mcp_server` reserved in `connector_type`, not built (LD-22) |
| BYO connector keys UX | Schema supports `credential_owner=tenant` from day one (LD-22); UX later |
| Redis cache | LD-5 context cache is in-process for the pilot (LD-21) |
| Multi-chain beyond BTC | Pilot loop is Bitcoin first (07 acceptance) |
| Workflow-template library | Post-pilot (07 deferrals) |
| Learning-Layer analytics | Capture only in pilot (LD-30) |
| Frontend build | Separate track: Lovable UX export → GitHub → build against the OpenAPI contract; Entra PKCE tested with a real token first (LD-26) |
| Ledger cross-entry hash chaining | Deferred by LD-3; per-entry SHA-256 + DB-level insert-only enforcement now |
| Orphaned-blob reaper | LD-4 tolerates orphaned blobs on ledger-transaction failure; periodic cleanup later |
| Deferred integrations: Codex portal, USSS deconflict, CoinTracking/Blockpit | Evidence-backed order, not Phase 1 (05 §4.3) |
| Dormant-wallet monitoring behavior | `wallets.is_watched` is a schema hook only (LD-13) |
