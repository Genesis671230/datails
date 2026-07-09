# Modules

What each backend block does. Updated as slices land.

## backend/app/core

- `config.py` — environment-driven settings; hard-fails if `AUTH_DEV_MODE` is
  set outside `ENVIRONMENT=local` (LD-1).
- `logging.py` — structured JSON logging with request-scoped context fields
  (request_id, tenant_id, workspace_id, actor_id).
- `errors.py` — domain error types + consistent error envelope; internals
  never leak to clients.
- `request_context.py` — per-request request_id assignment and access logging.
- `auth.py` — Entra JWT validation middleware (LD-1): signature/issuer/
  audience/expiry on every route except health; attaches claims, never
  provisions; JWKS cache; local-only dev bypass.

## backend/app/api

- `deps.py` — route dependencies: validated claims, DB session, resolved
  tenant context (from the token's oid only).
- `v1/health.py` — liveness; the only unauthenticated route (LD-1).
- `v1/workspaces.py` — bootstrap (the only provisioning path) and me.

Route handlers stay thin: validate schema, resolve context, call a service.

## backend/app/db

- `base.py` / `session.py` — declarative base, async engine/session; runtime
  connects as the restricted `datails_app` role (LD-3).
- `models/` — full Slice-0 core schema (28 tables): tenancy, methodology,
  cases, wallets (workspace-global + provenance labels, LD-13/14),
  connectors, traces (05 §8), append-only ledgers, workflow agents, usage,
  idempotency. `models/enums.py` holds the 25 domain enums (05 §1.3/1.3a).
- `repositories/` — persistence queries (users, tenancy).

## backend/app/services

Domain logic, one folder per domain (tenancy, onboarding, methodologies,
connectors, cases, findings, decisions, reports, ledgers, ai, usage).

- `tenancy/service.py` — workspace bootstrap (tenant → owner user → default
  workspace → onboarding session → methodology seed) and context resolution.
- `methodologies/baseline_seed.py` — AQ baseline methodology seed (05 §2,
  verbatim), applied to every new tenant.

## backend/app/fixtures

- `aq_case_placeholder.json` + `aq_case.py` — anonymised AQ case fixture
  (PLACEHOLDER until the real dataset arrives) and its loader.

## backend/app/integrations

External system clients. No business logic here; no AI logic in connectors
and vice versa. **Genericity rule (Slice 1 acceptance):** vendor knowledge
stays inside its `integrations/<vendor>/` package; `registry.py` is the only
module allowed to import vendor code; services see only the generic
contracts. Enforced by `tests/test_connector_genericity.py`.

- `generic_api/base.py` — generic contracts: ConnectorClient, ConnectorResult,
  NormalizedLabel/Transfer, plus the mock connector (LD-19).
- `crystal/client.py` — ALL Crystal knowledge: modes, normalization,
  replay/live transports (live gated on the LD-6 spike).
- `crystal/fixtures.py` + `crystal/fixtures/*.json` — recorded-response
  replay fixtures (synthetic and provisional until the LD-6 spike).
- `registry.py` — connector_type → client; the single vendor touchpoint.
- `blob_storage/` — BlobStorage interface + filesystem impl (Azure at Slice 3).
- `key_vault/` — SecretResolver interface + env-var impl (Key Vault at Slice 3).
- `factories.py` — settings-driven backend selection.

## Slice 1 service/route additions

- `core/idempotency.py` — LD-28 ASGI middleware (replay, 409 on conflict).
- `core/hashing.py` — canonical JSON + SHA-256 (LD-4 snapshots).
- `services/cases/`, `services/findings/`, `services/decisions/` — case
  domain; decision writes emit ledger events same-transaction (LD-9).
- `services/ledgers/writers.py` — non-committing ledger writers (callers own
  the transaction).
- `services/connectors/` — registry service (test call persists nothing,
  LD-18.2), LD-4 execution pipeline with LD-11/LD-22 limits, vendor-agnostic
  wallet lookup + attach with LD-14 label provenance.
- `api/v1/`: cases, findings, decisions, ledger, connectors routes.

## backend/scripts

- `export_openapi.py` — writes `docs/openapi.json`, the frontend contract
  (LD-26).
