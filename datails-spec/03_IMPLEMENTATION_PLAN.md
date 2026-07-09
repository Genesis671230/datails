# Datails — Backend Implementation Plan for Claude Code

## Purpose

This document is the execution plan for building the first production-shaped backend for Datails.

It should be used together with:

- the product/build specification,
- the auditable architecture specification,
- and the repository itself.

This file translates the architecture into:

- exact implementation order,
- exact modules,
- exact tables,
- exact routes,
- and hard checkpoints.

Claude Code must build in the order described here.
It must not jump ahead to "interesting" features while foundational pieces are incomplete.

*(Amendments in `04_ERRATA_LOCKED_DECISIONS.md` apply: LD-1 inserts Phase 2A; LD-7 swaps Phases 6 and 7; LD-8 adds ledger read endpoints; LD-10 adds test requirements to every checkpoint; LD-11 changes connector call accounting; LD-13/14 change the wallet schema — see `05_DOMAIN_MODEL.md`. **Per LD-26, the build SEQUENCE is now governed by `07_BUILD_PLAN.md`; this document remains the content reference for tables, routes, and rules. Per LD-21, all `digital_colleague*` names read as `workflow_agent*`.**)*

***

## Overall implementation principle

Build from the bottom up in stable layers:

1. App skeleton
2. Config and observability
3. Database and persistence
4. Auth/tenant scope
5. Core domain objects
6. Connectors and ingestion
7. Ledgers and provenance
8. AI orchestration
9. Reports and digital colleagues
10. Usage, deployment, and hardening

No later phase should begin until the previous one has passed its checkpoint.

***

## Required tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Pydantic
- Azure Identity SDK
- Azure Key Vault SDK
- Azure Blob Storage SDK
- Azure Foundry / Azure OpenAI-compatible SDK where applicable
- Docker
- GitHub Actions
- Bicep

***

## Repository target structure (canonical, per LD-2)

```text
backend/
  app/
    api/v1/
    core/
    db/
      models/
      repositories/
    services/
      tenancy/
      onboarding/
      methodologies/
      connectors/
      cases/
      findings/
      decisions/
      reports/
      ledgers/
      ai/
      usage/
    integrations/
      azure_foundry/
      key_vault/
      blob_storage/
      crystal/
      generic_api/
    schemas/
    tests/
    main.py
  alembic/
  Dockerfile
  requirements.txt
```

***

## Phase 0 — Repository and app skeleton

### Goal

Create a clean backend scaffold with explicit module boundaries.

### Deliverables

- FastAPI app initialized
- `/api/v1/health` route
- config loader
- structured logging setup
- error handling middleware
- Dockerfile
- docker-compose for local development
- README.md
- ARCHITECTURE.md
- MODULES.md
- DECISIONS.md

### Required files

- `app/main.py`
- `app/core/config.py`
- `app/core/logging.py`
- `app/core/errors.py`
- `app/api/v1/health.py`
- `Dockerfile`
- `docker-compose.yml`

### Checkpoint

This phase is complete only when:

- the app boots locally,
- `/api/v1/health` returns success,
- logging works,
- Docker build works,
- project documentation files exist.

***

## Phase 1 — Database foundation

### Goal

Create the database base, model registry, session management, and migration flow.

### Deliverables

- SQLAlchemy base
- async session setup
- Alembic initialized
- first migration working
- local PostgreSQL wired through docker-compose

### Required files

- `app/db/base.py`
- `app/db/session.py`
- `alembic.ini`
- `alembic/env.py`

### Checkpoint

This phase is complete only when:

- database container runs,
- the backend connects successfully,
- an initial migration can be generated and applied,
- rollback works.

***

## Phase 2 — Identity, tenancy, and workspace scope

### Goal

Introduce the fundamental isolation model.

### Tables to create

#### tenants

- id (uuid, pk)
- slug
- name
- plan
- trial_ends_at
- is_active
- metadata
- created_at
- updated_at

#### users

- id (uuid, pk)
- tenant_id (fk)
- external_auth_id
- email
- display_name
- role
- is_active
- last_login_at
- created_at

#### workspaces

- id (uuid, pk)
- tenant_id (fk)
- name
- workspace_type
- is_default
- settings_json
- created_at
- updated_at

#### onboarding_sessions

- id (uuid, pk)
- tenant_id (fk)
- user_id (fk)
- status
- started_at
- completed_at
- payload_json

### Required routes

- `GET /api/v1/health`
- `POST /api/v1/workspaces/bootstrap`
- `GET /api/v1/workspaces/me`

### Required services

- tenancy service
- workspace bootstrap service
- auth context resolver

### Checkpoint

Complete only when:

- one user can be associated with one tenant,
- one default workspace can be created,
- every request can resolve tenant/workspace context.

*(Phase 2A — Entra JWT validation middleware — follows immediately, per LD-1.)*

***

## Phase 3 — Methodology capture

### Goal

Store investigator methodology in structured form.

### Tables to create

#### methodologies

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- name
- specialty
- report_style
- jurisdictions_json
- trusted_tools_json
- version
- is_active
- created_at
- updated_at

#### methodology_steps

- id (uuid, pk)
- methodology_id (fk)
- step_order
- step_name
- description
- tool_preference
- output_type
- requires_human_approval
- created_at

#### generated_templates

- id (uuid, pk)
- methodology_id (fk)
- template_type
- template_name
- template_body
- version
- created_at

#### digital_colleague_profiles

- id (uuid, pk)
- methodology_id (fk)
- colleague_type
- instructions
- allowed_tools_json
- allowed_outputs_json
- approval_required
- created_at

### Required routes

- `POST /api/v1/onboarding/methodology`
- `GET /api/v1/methodologies/current`
- `PUT /api/v1/methodologies/current`

### Checkpoint

Complete only when:

- methodology can be submitted,
- methodology steps are structured,
- a current methodology can be fetched and updated.

***

## Phase 4 — Connector registry and secret resolution

### Goal

Prepare secure connection to customer-owned tools.

### Tables to create

#### connectors

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- name
- connector_type
- base_url
- auth_type
- secret_ref
- status
- daily_call_limit
- metadata_json
- created_at
- updated_at

*(`calls_today` and reset logic removed per LD-11; daily usage is derived from `connector_runs`.)*

#### connector_runs

- id (uuid, pk)
- connector_id (fk)
- tenant_id (fk)
- workspace_id (fk)
- triggered_by_user_id (nullable fk)
- status
- request_ref
- response_ref
- started_at
- completed_at
- error_message

### Required integrations

- Key Vault secret resolver
- connector registry service
- generic connector execution base class

### Required routes

- `POST /api/v1/connectors`
- `GET /api/v1/connectors`
- `POST /api/v1/connectors/{id}/test`

### Checkpoint

Complete only when:

- connectors can be registered,
- secret references resolve through Key Vault,
- a test call can be executed without secrets stored in DB.

***

## Phase 5 — Case domain

### Goal

Build the operational object model around cases.

### Tables to create

*(Wallet schema amended by LD-13/LD-14 — see `05_DOMAIN_MODEL.md` for the canonical `wallets`, `case_wallets`, and `wallet_labels` definitions.)*

#### cases

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- created_by (fk)
- title
- case_type
- status
- priority
- summary
- context_snapshot_json
- metadata_json
- created_at
- updated_at

#### evidence_items

- id (uuid, pk)
- case_id (fk)
- tenant_id (fk)
- evidence_type
- title
- storage_ref
- source_ref
- metadata_json
- created_at

#### findings

- id (uuid, pk)
- case_id (fk)
- tenant_id (fk)
- created_by (fk)
- finding_type
- title
- content
- source_ref
- confidence
- is_ai_generated
- approved_by
- approved_at
- created_at

#### decisions

- id (uuid, pk)
- case_id (fk)
- tenant_id (fk)
- made_by (fk)
- decision_type
- description
- rationale
- inputs_ref_json
- outcome
- created_at

### Required routes

- `POST /api/v1/cases`
- `GET /api/v1/cases`
- `GET /api/v1/cases/{id}`
- `PUT /api/v1/cases/{id}`
- `POST /api/v1/cases/{id}/wallets`
- `POST /api/v1/cases/{id}/evidence`
- `POST /api/v1/findings`
- `POST /api/v1/decisions`

### Checkpoint

Complete only when:

- a case can be created,
- wallets and evidence can be attached,
- findings and decisions can be recorded,
- a case retrieval endpoint returns coherent state, explicitly including the case's findings and decisions (per LD-8).

***

## Phase 6 — Blob storage snapshots *(swapped with former Phase 7 per LD-7)*

### Goal

Ensure external/raw payloads are stored in tenant-controlled storage.

### Required behavior

For every important connector retrieval:

1. raw payload is saved to Blob Storage,
2. hash is computed,
3. storage path is returned,
4. data ledger entry is created (in Phase 7, once ledgers exist).

### Required integrations

- Azure Blob storage client wrapper
- payload serializer/hash utility

### Checkpoint

Complete only when:

- a connector response can be snapshotted,
- hash computed and stored,
- storage reference returned for later ledger linkage.

***

## Phase 7 — Data Ledger and Decision Ledger *(swapped with former Phase 6 per LD-7)*

### Goal

Make provenance and durable history explicit.

### Tables to create

#### data_ledger

- id (bigserial pk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (nullable fk)
- connector_id (nullable fk)
- source_type
- source_ref
- payload_hash
- storage_ref
- retrieved_by_user_id (nullable fk)
- created_at

#### decision_ledger

- id (bigserial pk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (fk)
- decision_id (nullable fk)
- event_type
- actor_id (nullable fk)
- actor_type
- inputs_ref_json
- approved
- created_at

#### ai_call_log

- id (bigserial pk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (nullable fk)
- digital_colleague_id (nullable fk)
- task_type
- model_name
- tool_refs_json
- prompt_hash
- response_hash
- token_input
- token_output
- latency_ms
- status
- created_at

### Required services

- data ledger writer
- decision ledger writer
- AI call logger

### Required routes (per LD-8)

- `GET /api/v1/ledger/data?case_id=&connector_id=&limit=&offset=`
- `GET /api/v1/ledger/decision?case_id=&limit=&offset=`

### Checkpoint

Complete only when:

- connector data can be written to storage and logged,
- decisions generate ledger events (in the same transaction, per LD-9),
- AI calls can be logged independently of route code,
- ledger tables reject UPDATE/DELETE at the database level (per LD-3),
- ledger read endpoints return tenant-scoped entries.

***

## Phase 8 — Crystal integration

*(Gated by the LD-6 API spike. Connector definition corrected by LD-16 — no "Tier 1/Tier 2"; see `05_DOMAIN_MODEL.md`.)*

### Goal

Provide the first real external intelligence connector.

### Requirements

- Crystal connector service module
- endpoint for wallet lookup
- optional attach-to-case flow
- response normalization for selected fields
- raw snapshot storage
- ledger entry creation

### Suggested routes

- `POST /api/v1/connectors/crystal/wallet-lookup`
- `POST /api/v1/connectors/crystal/wallet-lookup-and-attach`

### Checkpoint

Complete only when:

- a wallet lookup succeeds,
- raw result is snapshotted,
- data ledger entry exists,
- and selected results can attach to a case.

***

## Phase 9 — Case context builder

### Goal

Create reusable case-grounding context for AI.

### Required behavior

The context builder should assemble:

- case summary,
- wallets,
- evidence references,
- top findings,
- relevant decisions,
- methodology cues,
- source references.

*(Inclusion priority, token budget, and staleness rules fixed by LD-5.)*

### Required files

- `services/ai/context_builder.py`

### Rules

- context assembly must not happen ad hoc in route handlers,
- context builder must be reusable across reports and agents,
- source references must be preserved.

### Checkpoint

Complete only when:

- one service can return a coherent case context payload for a case.

***

## Phase 10 — Azure Foundry integration

### Goal

Enable AI tasks using Azure-hosted models.

### Required integrations

- Foundry client wrapper
- model routing config
- task executor

### Initial task types

- case summarization
- report drafting
- finding draft generation
- research assistant response over scoped case context

### Required files

- `integrations/azure_foundry/client.py`
- `services/ai/task_executor.py`
- `services/ai/model_router.py`

### Required routes (per LD-20)

- `POST /api/v1/ai/assistant` — case-scoped assistant task (case_id required; context via context builder; logged to ai_call_log)

### Rules

- no direct model calls from routes,
- all model calls go through the Foundry wrapper,
- every run must log into `ai_call_log`.

### Checkpoint

Complete only when:

- backend can execute one Foundry task,
- response is returned,
- ai_call_log entry is created,
- the assistant route returns a case-grounded draft with source references.

***

## Phase 11 — Digital colleagues

### Goal

Create named, scoped AI assistants.

### Tables to create

#### digital_colleagues

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- colleague_type
- name
- description
- role_instructions
- allowed_tools_json
- allowed_actions_json
- approval_required
- is_active
- created_at

#### digital_colleague_runs

- id (uuid, pk)
- digital_colleague_id (fk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (nullable fk)
- task_type
- input_ref_json
- output_ref_json
- status
- started_at
- completed_at

### Initial colleague types

- intake_analyst
- report_writer
- compliance_analyst
- research_analyst

### Required routes

- `GET /api/v1/digital-colleagues`
- `POST /api/v1/digital-colleagues/{id}/run`

### Checkpoint

Complete only when:

- one digital colleague can run against one case,
- the run is logged,
- the output is stored or attached appropriately,
- and approval rules are respected.

***

## Phase 12 — Reports and versioning

### Goal

Create production-shaped report generation.

### Tables to create

#### reports

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (fk)
- report_type
- title
- status
- current_version_id (nullable fk)
- created_by (fk)
- created_at
- updated_at

#### report_versions

- id (uuid, pk)
- report_id (fk)
- version_number
- content_markdown
- content_json
- source_refs_json
- generated_by_ai
- created_by (nullable fk)
- created_at

### Required routes

- `POST /api/v1/reports/draft`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/reports/{id}/versions`
- `POST /api/v1/reports/{id}/approve`

### Checkpoint

Complete only when:

- a report draft can be created from case context,
- versions are stored,
- a human can approve/finalize a draft state.

***

## Phase 13 — Usage metering

### Goal

Track usage for Azure credit monitoring and future billing.

### Tables to create

#### usage_records

- id (bigserial pk)
- tenant_id (fk)
- workspace_id (fk)
- case_id (nullable fk)
- category
- subcategory
- quantity
- unit
- cost_estimate
- ref_json
- created_at

#### tenant_plan_state

- tenant_id (pk/fk)
- current_plan
- usage_limit_json
- usage_state_json
- updated_at

### Required behavior

- AI tasks create usage records
- connector runs create usage records where relevant
- report generation can create usage records

### Required routes

- `GET /api/v1/usage/summary`

### Checkpoint

Complete only when:

- usage records exist,
- tenant summary can be returned.

***

## Phase 14 — Audit middleware and structured logging hardening

### Goal

Ensure every meaningful request is inspectable.

### Required behavior

Every request should be assigned:

- request_id
- tenant_id where available
- actor_id where available
- route/action metadata

### Required outputs

- structured logs
- consistent error shape
- meaningful operational trace

### Checkpoint

Complete only when:

- failed and successful requests are traceable,
- request correlation is possible.

***

## Phase 15 — Deployment and CI/CD

### Goal

Deploy backend safely into Azure.

### Required deliverables

- GitHub Actions workflow
- environment separation (dev/prod)
- Bicep templates for core resources
- container build + push flow

### Infrastructure targets

- Azure Container Apps
- PostgreSQL Flexible Server
- Key Vault
- Blob Storage
- Azure Foundry
- optionally API Management

### Required files

- `.github/workflows/deploy.yml`
- `infra/bicep/main.bicep`

### Checkpoint

Complete only when:

- one branch-to-Azure deployment path works,
- backend can run in Azure and connect to required services.

***

## Exact initial endpoint list

```text
GET    /api/v1/health
POST   /api/v1/workspaces/bootstrap
GET    /api/v1/workspaces/me
POST   /api/v1/onboarding/methodology
GET    /api/v1/methodologies/current
PUT    /api/v1/methodologies/current
POST   /api/v1/connectors
GET    /api/v1/connectors
POST   /api/v1/connectors/{id}/test
POST   /api/v1/connectors/crystal/wallet-lookup
POST   /api/v1/connectors/crystal/wallet-lookup-and-attach
POST   /api/v1/cases
GET    /api/v1/cases
GET    /api/v1/cases/{id}
PUT    /api/v1/cases/{id}
POST   /api/v1/cases/{id}/wallets
POST   /api/v1/cases/{id}/evidence
POST   /api/v1/findings
POST   /api/v1/decisions
GET    /api/v1/ledger/data
GET    /api/v1/ledger/decision
POST   /api/v1/ai/assistant
POST   /api/v1/cases/{id}/traces
GET    /api/v1/traces/{id}
POST   /api/v1/traces/{id}/hops/{hop_id}/confirm
POST   /api/v1/traces/{id}/hops/{hop_id}/reject
GET    /api/v1/workflow-agents
POST   /api/v1/workflow-agents/{id}/run
POST   /api/v1/reports/draft
GET    /api/v1/reports/{id}
GET    /api/v1/reports/{id}/versions
POST   /api/v1/reports/{id}/approve
GET    /api/v1/usage/summary
```

*(No `/auth` routes: Entra handles login; the backend validates JWTs per LD-1.)*

***

## Required service modules summary

```text
services/tenancy/
services/onboarding/
services/methodologies/
services/connectors/
services/cases/
services/findings/
services/decisions/
services/reports/
services/ledgers/
services/ai/
services/usage/
```

Each folder should contain focused service files rather than one giant file.

***

## Required documentation discipline

Claude Code must keep these updated:

- `README.md`
- `ARCHITECTURE.md`
- `MODULES.md`
- `DECISIONS.md`

### Additional recommended file

- `IMPLEMENTATION_STATUS.md`

This file should mark:

- completed phases,
- current phase,
- open blockers,
- next milestone.

***

## Hard stop rules

Claude Code must not move to later phases if any of the below are not true:

- app boots,
- migrations work,
- tenant scope works,
- connectors do not leak secrets,
- ledgers exist,
- AI calls are logged,
- storage snapshots work,
- routes stay thin,
- service boundaries remain clear.

***

## Final instruction

Build the Datails backend as a **reviewable, modular, traceable system**.

Do not optimize for speed by collapsing layers.
Do not hide logic in prompts or routes.
Do not create "temporary" shortcuts that damage clarity.

Each phase must end in a backend that is:

- runnable,
- understandable,
- testable,
- and safe to continue building on.
