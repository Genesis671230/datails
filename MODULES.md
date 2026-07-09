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

## backend/app/api/v1

Thin route handlers only: validate schema, resolve auth/tenant context, call
a service, return a response.

- `health.py` — liveness; the only unauthenticated route (LD-1).

## backend/app/db

SQLAlchemy async base, session management, models, repositories.

## backend/app/services

Domain logic, one folder per domain (tenancy, onboarding, methodologies,
connectors, cases, findings, decisions, reports, ledgers, ai, usage).

## backend/app/integrations

External system clients (azure_foundry, key_vault, blob_storage, crystal,
generic_api). No business logic here; no AI logic in connectors and vice
versa.
