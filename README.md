# Datails Backend

Case-centric Operational AI Workspace for digital asset investigations and
compliance. Built per the specification package in `datails-spec/` (eight
files; `04_ERRATA_LOCKED_DECISIONS.md` is binding, `07_BUILD_PLAN.md` governs
sequence).

## Repository layout

- `backend/` — FastAPI backend (canonical tree per LD-2)
- `infra/bicep/` — Azure infrastructure templates (region-parameterized, LD-23)
- `datails-spec/` — the frozen specification package
- `docs/build-log/` — one entry per completed slice
- `IMPLEMENTATION_STATUS.md` — current slice, blockers, next milestone
- `BACKLOG.md` — deferred items, each with a reason

## Run locally

Prerequisites: Docker Desktop, Python 3.12.

```bash
# Full stack (Postgres + backend)
docker compose up --build

# Or: run Postgres in Docker, backend on the host
docker compose up -d db
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
AUTH_DEV_MODE=true uvicorn app.main:app --reload
```

Health check: `curl http://localhost:8000/api/v1/health`

## Authentication (LD-1)

Every route except `/api/v1/health` requires a Microsoft Entra External ID
JWT. There are no `/auth` routes — Entra handles login; the backend validates.
For local development only, `AUTH_DEV_MODE=true` (with `ENVIRONMENT=local`)
bypasses validation with a fixed dev identity; the app refuses to start with
this flag in any other environment.

## Tests

```bash
cd backend
docker compose -f ../docker-compose.yml up -d db
pytest app/tests
```

## Documentation

- `ARCHITECTURE.md` — system overview and layers
- `MODULES.md` — what each backend block does
- `DECISIONS.md` — architectural choices and rationale
