#!/bin/sh
# Run the backend locally with REAL Entra External ID validation (LD-1) —
# no dev bypass. Used by the LD-26 PKCE real-token test.
# Issuer and JWKS come from the tenant's OIDC discovery document; the
# audience is the API app registration's client ID.
set -e
cd "$(dirname "$0")/.."

TENANT_ID=194ac953-cb8a-4e07-9890-65e73d2c024d

export ENVIRONMENT=local
export AUTH_DEV_MODE=false
export ENTRA_TENANT_ID="$TENANT_ID"
export ENTRA_AUTHORITY="https://${TENANT_ID}.ciamlogin.com/${TENANT_ID}/v2.0"
export ENTRA_JWKS_URL="https://datails.ciamlogin.com/${TENANT_ID}/discovery/v2.0/keys"
export ENTRA_AUDIENCE="00d8c4ff-db9c-4533-b344-48e08cf3af73"
export DATABASE_URL="postgresql+asyncpg://datails_app:datails_app_local@localhost:5432/datails"
export DATABASE_MIGRATION_URL="postgresql+asyncpg://datails_owner:datails_owner_local@localhost:5432/datails"

exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
