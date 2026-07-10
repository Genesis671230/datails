# Runbook (LD-29)

Operational procedures for the Datails pilot. Azure-specific commands are
completed at the Slice 3 deploy; the placeholders below name exactly what
gets filled in.

## Rollback (Azure Container Apps, LD-25)

ACA keeps prior revisions; rollback = shift traffic to the previous revision:

```bash
az containerapp revision list -n <app> -g <rg> -o table
az containerapp ingress traffic set -n <app> -g <rg> \
  --revision-weight <previous-revision>=100
```

Filled in at deploy: app name, resource group, and the one-liner in CI.

## Crystal key rotation (LD-22)

The shared temporary key lives in Key Vault as `crystal-api-key`. Rotation is
a secret version swap — zero code change:

```bash
az keyvault secret set --vault-name <kv> --name crystal-api-key --value <new-key>
```

The backend resolves the secret per call (no restart needed). Local
development: update `CRYSTAL_API_KEY` in `backend/.env`.

## When the demo breaks — checklist

1. `GET /api/v1/health` — app up? `database` field ok?
2. `docker compose ps` / ACA revision status — containers healthy?
3. Failed Crystal calls: `GET /api/v1/ledger/data` empty where it shouldn't
   be → check `connector_runs.error_message` (status `failed` rows carry the
   upstream error) and the shared-key daily budget (429 =
   `limit_exceeded`).
4. Failed AI calls: `ai_call_log.status = 'failed'` rows; check the Foundry
   endpoint and quota (App Insights query at deploy).
5. Trace stuck in `failed`: resume by re-POSTing confirm on the last
   confirmed hop (retries the proposal only; LD-27).
6. Trace stuck in `awaiting_confirmation`: that is human pace, not a defect
   (LD-27) — no timeout by design.
7. 401s everywhere: JWKS reachable? Entra authority/audience config drift?
8. Idempotency 409s: the client reused a key with a changed payload — new
   key, not a retry bug.

## Backups (verified at deploy)

- PostgreSQL Flexible Server: PITR via backup retention (Bicep).
- Blob Storage: soft-delete (30 days) + versioning (Bicep).
- Verify after first deploy: restore drill on a scratch database.
