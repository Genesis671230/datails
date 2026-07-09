# Implementation Status

Last updated: 9 July 2026

## Completed slices

- **Slice 0 — Foundation** (9 Jul 2026): scaffold, full core schema (28
  tables, one migration, LD-3 insert-only enforcement), Entra JWT middleware
  (LD-1) + bootstrap/me, AQ methodology seed + placeholder AQ case fixture +
  synthetic Crystal fixtures, OpenAPI contract, Bicep skeleton, CI workflow.
  30 tests green. Details: `docs/build-log/2026-07-09-slice-0.md`.

## Current slice

**Slice 1 — Case + Crystal ingestion** (next up)

First live moment: wallet in → enriched case.

- [ ] Case domain routes (03 Phase 5 list); `GET /api/v1/cases/{id}` returns
      findings + decisions (LD-8)
- [ ] Decision writes emit ledger events same-transaction (LD-9)
- [ ] Connector interface + Crystal connector (risk_check /
      full_investigation modes, LD-22); Key Vault secret resolution;
      LD-4 ingestion sequence; wallet-lookup + attach routes; label writes
      with provenance (LD-14)
- [ ] Shared-key global budget + per-connector daily limit (LD-11/22)
- [ ] Idempotency middleware on expensive POSTs (LD-28)

## Open blockers

- None. Local mocks cover Blob Storage and Key Vault until Azure resources
  exist; CI runs on recorded (currently synthetic) Crystal fixtures.

## Awaiting from founder (asked when a slice needs them)

- **Slice 1:** Crystal temporary API key → Key Vault (LD-22) — required only
  for the live-call acceptance check
- **Before Slice 2:** GPT-4o + GPT-4o-mini West Europe deployments verified,
  incl. quota (LD-23/24)
- **Slice 3:** Azure resource group (West Europe), Entra External ID app
  registration, GitHub repository + Actions OIDC federation
- **Anytime:** anonymised AQ case dataset (replaces placeholder fixture);
  cohort Data & Methodology Permission status per member (gates
  `learning_capture_enabled`, LD-30)

## Next milestone

Slice 1 acceptance: real Crystal call round-trips (snapshot → hash →
data_ledger → labels with provenance, visible via `GET /api/v1/ledger/data`);
idempotency replay returns the original response; CI green on fixtures.
