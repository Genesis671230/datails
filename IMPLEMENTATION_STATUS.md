# Implementation Status

Last updated: 9 July 2026

## Completed slices

- (none yet)

## Current slice

**Slice 0 — Foundation** (in progress)

- [x] Repo scaffold: FastAPI app, config, structured logging, error
      middleware, `/api/v1/health`, Dockerfile, docker-compose with Postgres
- [ ] DB foundation: SQLAlchemy async base/session, Alembic
- [ ] Full core schema in one migration + LD-3 insert-only enforcement
- [ ] Entra JWT middleware (LD-1) + `POST /api/v1/workspaces/bootstrap` +
      `GET /api/v1/workspaces/me`
- [ ] Methodology seed (AQ baseline) + AQ case fixture (placeholder) +
      recorded Crystal fixtures (synthetic, pending LD-6 spike)
- [ ] OpenAPI export, Bicep skeleton (region param, PITR, Blob soft-delete),
      CI workflow

## Open blockers

- None for Slice 0. Azure/Entra/Crystal prerequisites are provided later by
  the founder; Slices 0–2 build and test locally against Docker.

## Awaiting from founder (asked when a slice needs them)

- Azure resource group (West Europe) — needed at Slice 3 deploy
- Foundry GPT-4o / GPT-4o-mini deployments verified — needed before Slice 2
- Entra External ID app registration — needed for deployed auth + frontend
  contract; local tests use test-signed JWTs against the real validation path
- Crystal temporary API key — needed at Slice 1 for the live round-trip
- Anonymised AQ case dataset — placeholder fixture used until it arrives

## Next milestone

Slice 0 acceptance: app boots; migration up/down clean; ledger tables reject
UPDATE/DELETE; valid Entra JWT → tenant context, missing/invalid → 401;
tenant-isolation test passes; fixtures load; CI green.
