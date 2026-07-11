# Runbook (LD-29)

Operational procedures for the Datails pilot stamp
(`datails-dev`, **swedencentral**). Backend:
`https://datails-dev-api.ambitiousglacier-9ed1fc18.swedencentral.azurecontainerapps.io`

## Deploy (how releases happen)

Push to `main` → CI (lint + 117 tests vs Postgres) → deploy job (OIDC, no
stored credentials): `az acr build` (image `datails-backend:<sha>` in
`datailsdevacr`) → migration job `datails-dev-migrate` (alembic upgrade head,
polled to completion; deploy aborts if it fails) → new revision on
`datails-dev-api` → health smoke on the FQDN.

## Rollback (Azure Container Apps, LD-25)

The app runs in **multiple-revision mode**; rollback is a traffic shift, no
rebuild. **Drilled successfully 11 Jul 2026** (revision `--0000001` ↔
`--dbfix`): old revision served healthy with auth enforced, then rolled
forward; total drill time ≈ 1 minute.

```bash
# 1. See revisions (newest first)
az containerapp revision list -g datails-dev -n datails-dev-api --all \
  --query 'reverse(sort_by([], &properties.createdTime))[].{name:name, active:properties.active, image:properties.template.containers[0].image}' -o table

# 2. If the previous revision is inactive, activate it
az containerapp revision activate -g datails-dev -n datails-dev-api --revision <previous>

# 3. Shift all traffic to it (THE rollback moment)
az containerapp ingress traffic set -g datails-dev -n datails-dev-api \
  --revision-weight <previous>=100 <current>=100:0   # e.g. <previous>=100 <current>=0

# 4. Verify
curl https://datails-dev-api.ambitiousglacier-9ed1fc18.swedencentral.azurecontainerapps.io/api/v1/health

# 5. Roll forward later by reversing the weights, then deactivate the old revision
```

Caveat: if the bad release included a migration, traffic rollback does NOT
undo the schema — check `alembic downgrade` implications first (ledger
tables are insert-only; migrations are designed to be additive).

## Crystal key rotation (LD-22)

The shared temporary key lives in Key Vault `datails-dev-kv` as
`crystal-api-key` (created when the key arrives). Rotation is a secret
version swap — zero code change:

```bash
az keyvault secret set --vault-name datails-dev-kv --name crystal-api-key --value <new-key>
```

The backend resolves per call. Note: Container Apps re-resolves Key
Vault-referenced secrets only on a new revision or ~every 30 minutes — for
env-injected secrets (`database-url`, `foundry-api-key`) force a revision:
`az containerapp update -g datails-dev -n datails-dev-api --revision-suffix rot<N>`.

## Secrets inventory (Key Vault `datails-dev-kv`)

| Secret | Used by |
|---|---|
| `postgres-admin-password` | migrations (owner role) |
| `database-url` | app runtime (restricted `datails_app` role, LD-3) |
| `database-migration-url` | migrate job |
| `foundry-api-key` | AI backend (managed identity replaces this later) |

## When the demo breaks — checklist

1. `GET /api/v1/health` — app up? `database` field ok? (`unavailable` right
   after a secret rotation = stale KV reference → force a new revision.)
2. `az containerapp revision list …` — revision healthy/active?
3. Failed Crystal calls: `GET /api/v1/ledger/data` missing entries →
   `connector_runs.error_message` has the upstream error; 429 =
   `limit_exceeded` (per-connector daily limit or shared-key budget, LD-22).
4. Failed AI calls: `ai_call_log.status='failed'` rows; check Foundry quota
   (`datails-dev-foundry`, deployments `gpt-5-4`/`gpt-5-mini`).
5. Trace stuck in `failed`: re-POST confirm on the last confirmed hop
   (retries the proposal only, LD-27).
6. Trace in `awaiting_confirmation`: human pace, not a defect — no timeout
   by design (LD-27).
7. 401s everywhere: Entra JWKS reachable? Authority/audience drift? Compare
   `backend/scripts/run_backend_entra.sh` values with the app's env.
8. Idempotency 409: client reused a key with a different payload — new key,
   not a retry bug.
9. DB access for founder debugging: firewall rule `founder-dev` on
   `datails-dev-pg` (IP-scoped; refresh with
   `az postgres flexible-server firewall-rule create -g datails-dev -s datails-dev-pg -n founder-dev --start-ip-address <ip> --end-ip-address <ip>`).

## Backups (verified in Bicep, LD-29)

- PostgreSQL Flexible Server `datails-dev-pg`: 14-day backup retention (PITR).
- Blob `datailsdevsnap`: soft-delete 30 days + versioning.
- TODO before cohort data: one restore drill on a scratch database.

## Log queries (Log Analytics `datails-dev-logs`)

```bash
# Backend console logs (structured JSON lines)
az monitor log-analytics query -w <workspace-customer-id> --analytics-query \
  "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'datails-dev-api' | order by _timestamp_d desc | take 50 | project Log_s"

# Migration job output
az monitor log-analytics query -w <workspace-customer-id> --analytics-query \
  "ContainerAppConsoleLogs_CL | where ContainerJobName_s == 'datails-dev-migrate' | order by _timestamp_d desc | take 50 | project Log_s"
```
