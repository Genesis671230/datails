# Architecture

Datails backend: a modular, auditable, case-centric system. The object model
— cases, wallets, findings, decisions, reports, connectors, ledgers, workflow
agents — is the product; chat is one interface into it.

## Layers (per 02_ARCHITECTURE_SPEC.md)

1. **Identity, tenancy, access** — Entra External ID JWT validation (LD-1),
   tenant scope on every customer-facing record, roles: owner / investigator /
   analyst / viewer.
2. **Data ingress and connectors** — customer-owned tools; secrets in Key
   Vault only; every retrieval snapshotted to Blob and registered in the Data
   Ledger (LD-4 sequence).
3. **Operational state / object model** — durable business objects in
   PostgreSQL, tenant-scoped, explicit relationships.
4. **AI orchestration** — Azure AI Foundry only; scoped context via one
   context builder (LD-5); every call logged to `ai_call_log`.
5. **Governance, provenance, audit** — append-only ledgers enforced at the
   database level (LD-3); decision writes emit ledger events in the same
   transaction (LD-9); human gates on high-trust outputs.
6. **Deployment and operations** — Docker → Azure Container Apps (LD-25),
   one regional stamp (West Europe, LD-23), Bicep with PITR and Blob
   soft-delete from the first deployment (LD-29).

## Request flow

```
request → RequestContextMiddleware (request_id, log context)
        → EntraJwtMiddleware (validate token; /api/v1/health exempt)
        → route handler (thin: validate schema, resolve context, call service)
        → service (domain logic; ledger writes, AI logs, snapshots explicit)
        → repository (persistence)
```

Tenant context derives only from the validated token — never from
client-supplied bodies, params, or headers (LD-1).

## Database roles

Two Postgres roles: `datails_owner` runs migrations; `datails_app` is the
runtime role and holds INSERT+SELECT only on the four append-only tables
(`data_ledger`, `decision_ledger`, `ai_call_log`, `learning_events`), plus
triggers rejecting UPDATE/DELETE as defense in depth (LD-3, LD-30).

## Build order

Four slices per `datails-spec/07_BUILD_PLAN.md` (LD-26). Current status:
`IMPLEMENTATION_STATUS.md`.
