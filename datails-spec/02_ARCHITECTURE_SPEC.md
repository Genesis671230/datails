# Datails — Claude Code Auditable Architecture Spec

*(Per LD-21, "digital colleagues" and all `digital_colleague*` names in this document read as workflow agents / `workflow_agent*`.)*

## Purpose of this document

This document is the operating instruction for Claude Code to build the Datails backend in a way that is:

- modular,
- reviewable by a future senior engineer,
- traceable,
- auditable,
- Azure-native,
- and safe for sensitive digital-asset investigation environments.

The goal is not only to produce working code.
The goal is to produce a backend that can later be:

- inspected,
- refactored,
- extended,
- certified internally,
- and trusted in high-sensitivity environments.

This means Claude Code must not generate a tangled prototype.
It must generate a **block-based system with explicit boundaries, logging, provenance, and readable code paths**.

***

## Primary rule

**No spaghetti code.**

Every feature must belong to a clearly named module.
Every module must have a single primary responsibility.
Every module must expose clear interfaces.
Every important action must be logged.
Every AI output must lead back to a source.
Every external connector action must be snapshotted into tenant-controlled storage before it becomes part of the operational state.

If a senior engineer opens the repository later, they should be able to understand:

1. what each block does,
2. how blocks communicate,
3. where data enters,
4. how data becomes case state,
5. how AI interacts with that state,
6. and how the system proves why something happened.

***

## Product we are building

Datails is a **case-centric Operational AI Workspace for digital asset investigations and compliance**.

It is not a generic chatbot.
It is not a generic workflow builder.
It is not an autonomous investigator.

The product is centered on operational objects:

- cases,
- wallets,
- evidence,
- findings,
- decisions,
- reports,
- connectors,
- data ledger entries,
- and digital colleagues.

The guiding product principle is:

> **The object model is the product. Chat is only one interface into it.**

The guiding user promise is:

> **You never explain your case twice.**

That means the backend must preserve state, context, provenance, and continuity.

***

## Architectural philosophy

The system must be built as a set of **separable layers**.

### Layer 1 — Identity, tenancy, and access

Responsible for:

- who the user is,
- which tenant/workspace they belong to,
- what they can access,
- and which actions they are allowed to perform.

### Layer 2 — Data ingress and connector execution

Responsible for:

- external API calls,
- MCP-style tool connections,
- file ingestion,
- connector secrets,
- storage snapshot creation,
- and registration in the Data Ledger.

### Layer 3 — Operational state and object model

Responsible for:

- durable business objects,
- case state,
- relationships between objects,
- and state transitions.

### Layer 4 — AI orchestration and agent execution

Responsible for:

- selecting tools,
- selecting models,
- enforcing task boundaries,
- generating drafts,
- and attaching outputs back to the object model.

### Layer 5 — Governance, provenance, and audit

Responsible for:

- decision history,
- data provenance,
- AI execution logging,
- human approval tracking,
- and system inspectability.

### Layer 6 — Deployment, operations, and observability

Responsible for:

- health,
- environments,
- CI/CD,
- infrastructure as code,
- and production readiness.

These layers must stay conceptually distinct.

***

## Non-negotiable system rules

### 1. Tenant isolation first

Every customer-facing record must be tenant-scoped.
No data from one tenant may be accessible to another tenant unless an explicit sharing model is introduced later.

### 2. Cloud-safe by default

All runtime data stays inside the Azure environment controlled by Datails or the enterprise customer.

### 3. Connector data is imported into tenant-controlled storage

When API/MCP connectors are used, data must be pulled into the tenant's Azure-hosted environment, snapshotted, and referenced before it is relied on by agents or durable case logic.

### 4. Every meaningful action is inspectable

The system must always be able to answer:

- what happened,
- when,
- by whom or by what service,
- based on which source,
- using which tool,
- and using which model if AI was involved.

### 5. No hidden AI magic

Agents may assist, summarize, structure, and draft.
They may not silently make high-trust durable decisions.

### 6. Human-on-the-loop

Important outputs remain subject to user review, approval, or rejection.

### 7. Privacy-safe AI usage

Use Azure-hosted model infrastructure only in production. Sensitive customer data must not be routed through public consumer AI runtimes.

### 8. Enterprise readability over cleverness

Claude Code must favor simple, explicit, boring architecture over compact but opaque patterns.

***

## Coding standards Claude Code must follow

### General standards

- Use Python 3.11+
- Use FastAPI
- Use SQLAlchemy 2.x async
- Use Alembic for migrations
- Use Pydantic models for request/response schemas
- Use Docker for packaging
- Use GitHub Actions for deployment automation
- Use Bicep for Azure infrastructure definitions

### Readability rules

- No giant files when a domain can be separated cleanly
- No business logic directly inside route handlers
- No raw SQL spread across the codebase unless justified and isolated
- No connector logic inside AI orchestration modules
- No AI prompt strings scattered everywhere without structure
- No secrets in code
- No magic constants without named configuration

### Documentation rules inside code

Each important module must contain:

- a short top-level docstring saying what the module is for,
- comments only where they explain important architectural intent,
- named service classes or functions with explicit responsibilities.

### Explainability rule

Whenever Claude Code adds a new module, service, or route, it must also produce a brief explanation in commit/PR notes describing:

- what it added,
- why it belongs in that module,
- what other modules it depends on,
- and what data path it affects.

***

## Required repository shape

*(Superseded by the canonical tree in `03_IMPLEMENTATION_PLAN.md` per LD-2. Kept here for context of the intended separation of concerns.)*

This folder structure is deliberate.
It separates:

- routes,
- business logic,
- integrations,
- persistence,
- ledgers,
- and infrastructure.

***

## Required architectural blocks

## Block A — Identity, tenancy, and RBAC

### Purpose

Ensure every request is associated with:

- a user,
- a tenant,
- a workspace,
- and a permission context.

### Responsibilities

- authenticate user identity,
- resolve tenant membership,
- enforce workspace scoping,
- assign roles,
- check access rights.

### Rules

- No route may execute meaningful business logic without tenant context.
- Authorization must be checked before service execution.
- Role checks must be explicit.

### Minimal roles for Phase 1

- owner
- investigator
- analyst
- viewer

### Reviewability requirement

A senior engineer must be able to inspect one dedicated area of the codebase and understand how access is enforced.

***

## Block B — Onboarding and methodology capture

### Purpose

Capture how the investigator works so the workspace can adapt around them.

### Capture items

- investigation specialty,
- jurisdictions,
- trusted tools,
- report style,
- preferred workflow steps,
- exchange/contact preferences,
- desired AI assistance level.

### Output

This block should produce structured methodology records that later feed:

- report templates,
- digital colleague defaults,
- workflow suggestions.

### Rules

- Do not store methodology only as free text.
- Persist structured fields and steps.
- Preserve editability and versioning from the start.

***

## Block C — Connector execution layer

### Purpose

Connect customer-owned tools and ingest data into the tenant environment.

### Phase 1 connectors

- Crystal (as corrected by LD-16)
- one generic API connector
- file upload

### Connector execution flow

1. request arrives,
2. auth and tenancy are resolved,
3. connector credentials are resolved from Key Vault,
4. connector call executes,
5. raw response is snapshotted to tenant-controlled storage,
6. response hash is created,
7. Data Ledger entry is written,
8. normalized subset may be attached to case context.

### Rules

- Never persist raw connector secrets in database.
- Never let agents rely on untracked external data.
- Every external data retrieval must create a provenance trail.

### Reviewability requirement

A future engineer must be able to trace exactly how a Crystal API result entered the system and where it was stored.

***

## Block D — Operational object model

### Purpose

Represent the real durable product state.

### Primary objects

- Workspace
- Case
- Wallet
- Evidence item
- Finding
- Decision
- Report
- Connector
- Methodology
- Digital colleague

### Rules

- Cases are first-class objects, not chat threads.
- Findings are attached to cases.
- Decisions are append-only.
- Reports are versioned.
- AI outputs should attach to objects, not live only in conversations.

### State rule

If an AI action creates useful knowledge, it must either:

- be discarded,
- or be promoted into a durable object with provenance.

***

## Block E — Data Ledger

### Purpose

Create a durable provenance trail for imported and referenced data.

### Each ledger entry should capture

- tenant_id,
- workspace_id,
- case_id if applicable,
- connector_id,
- source type,
- source reference,
- retrieval timestamp,
- raw payload storage reference,
- content hash,
- retrieval actor or service.

### Rules

- Data Ledger must be append-oriented.
- It must not be overwritten casually.
- It is the source chain for evidence and AI grounding.

*(LD-3 hardens this: database-level insert-only enforcement.)*

***

## Block F — Decision Ledger

### Purpose

Record human and AI-assisted decisions in an inspectable way.

### Each ledger entry should capture

- tenant_id,
- workspace_id,
- case_id,
- decision type,
- made by,
- supported by which findings/data,
- whether AI-assisted,
- whether approved,
- timestamp.

### Rules

- Decisions are not mutable facts.
- If a decision changes, append a new decision event.
- Do not silently rewrite decision history.

***

## Block G — AI orchestration and digital colleagues

### Purpose

Run agents in a controlled, scoped, inspectable way.

### Initial digital colleagues

- Intake Analyst
- Report Writer
- Compliance Analyst
- Research Analyst

### AI orchestration rules

Each agent must have:

- a clear role,
- a clear allowed tool set,
- a clear allowed output type,
- a clear context boundary,
- a clear escalation / approval rule.

### Model routing rules

- Stronger reasoning models only for genuinely complex tasks.
- Cheaper models for formatting, rewriting, summarizing.
- No hidden model selection.
- The selected model must be logged.

### Tool rules

- Agent tools must be explicit.
- Connector access must be scoped.
- Case context must be scoped.
- Public/open-web retrieval must be separate from private case data retrieval.

### Output rules

Every AI-generated output must record:

- which agent created it,
- which model was used,
- which tools were used,
- which source references were relied upon,
- confidence if available,
- and whether human approval is required.

### Reviewability requirement

A senior engineer must be able to inspect one module and understand how the Report Writer differs from the Intake Analyst.

***

## Block H — Report generation

### Purpose

Generate high-value operational outputs grounded in case state and methodology.

### Phase 1 report types

- police intake report,
- exchange compliance report,
- investigator summary,
- structured case draft dossier.

*(LD-17 adds the freeze/blocklist request letter as a first-class report type.)*

### Rules

- Reports are drafts by default.
- Reports must be versioned.
- Source references should be preserved.
- Human review happens before finalization/export.

### Architecture rule

Report generation must use services, not route-level prompt calls.

***

## Block I — Usage metering

### Purpose

Measure system usage for credits, limits, and future billing.

### What to meter

- AI task runs,
- connector runs,
- report generations,
- storage-heavy operations,
- tenant-level totals.

### Rules

- Metering must be passive and reliable.
- It must not clutter business logic.
- Use dedicated usage services and records.

***

## Block J — Audit and observability

### Purpose

Make the system understandable and diagnosable.

### Must log

- auth events,
- connector runs,
- data ingestion,
- case writes,
- findings writes,
- decisions writes,
- report generation events,
- AI execution events,
- approval events,
- failures.

### Logging structure

Use structured logs with consistent fields:

- request_id
- tenant_id
- workspace_id
- case_id
- actor_id
- module
- action
- status
- timestamp

### Rule

Logs must help answer operational and compliance questions, not just debugging questions.

***

## Database design rules

### Rule 1 — Tenant scope on all customer-facing tables

Every customer-facing table includes tenant_id.

### Rule 2 — Explicit relationships

Foreign keys should be clear and intentional.
Avoid loose JSON blobs where structure matters.

### Rule 3 — Versioning where outputs evolve

Use version tables for reports and methodologies.

### Rule 4 — Append-only where history matters

Ledger and decision history should not rely on mutation.

### Rule 5 — JSON is allowed, but not as an excuse

JSON fields may be used for flexible metadata, not to avoid modeling core business structure.

***

## Service design rules

Every domain service should follow this pattern:

### Input

Typed input schema or explicit parameters.

### Processing

Domain logic inside the service layer only.

### Persistence

Repository layer or data access layer handles database interaction.

### Side effects

Ledger writes, AI call logs, storage snapshots, and usage records should happen in explicit service flows.

### Output

Typed response object or domain object.

This means route handlers should stay thin.

***

## Route handler rules

Route handlers must only do the following:

- accept request,
- validate request schema,
- resolve auth/tenant context,
- call service,
- return response.

Route handlers must not:

- contain major business logic,
- directly orchestrate connectors,
- directly call models,
- directly write ledgers across multiple domains,
- or mix unrelated responsibilities.

***

## AI prompt and orchestration design rules

### Rule 1 — Prompt assets must be organized

Prompt templates must live in explicit files or prompt modules.
Not scattered as raw strings.

### Rule 2 — Case context must be assembled intentionally

Build a context builder that prepares:

- case summary,
- key findings,
- relevant evidence,
- relevant wallet info,
- methodology cues,
- and source references.

*(LD-5 fixes the inclusion rules, token budget, and staleness policy.)*

### Rule 3 — Tool use is explicit

Agents may only use tools declared for them.

### Rule 4 — Source attribution is required

AI outputs should refer back to data ledger references, case objects, or connector snapshots.

### Rule 5 — Public knowledge separation

If open-web retrieval is ever used later, it must be clearly separated from private tenant data retrieval.

***

## Azure deployment architecture

### Frontend

Built in Lovable, exported to GitHub, deployed into your own Azure environment.

### Backend

Built via Claude Code, pushed to GitHub, deployed into Azure Container Apps.

### AI layer

Azure Foundry provides:

- model hosting/access,
- agent support,
- tool-oriented agent runtime where appropriate,
- AI governance support.

### Supporting Azure services

- Azure Container Apps
- Azure Database for PostgreSQL
- Azure Blob Storage
- Azure Key Vault
- Azure API Management
- Microsoft Entra ID / External ID
- Azure Monitor / Log Analytics

### Important clarification

Frontend and backend do **not** "merge inside Foundry."
They are deployed in Azure, and the backend integrates with Foundry.

***

## What Claude Code should build first

*(Superseded by the phase plan in `03_IMPLEMENTATION_PLAN.md` as amended by LD-1 and LD-7.)*

### Sprint 1 — skeleton and boundaries

- repository scaffold
- FastAPI app skeleton
- config management
- logging middleware
- error handling
- health endpoint
- Docker setup

### Sprint 2 — persistence foundation

- SQLAlchemy base models
- migration setup
- tenant/user/workspace schema
- repository patterns

### Sprint 3 — onboarding and methodology

- onboarding routes
- methodology schema
- methodology services

### Sprint 4 — connector ingestion

- Key Vault integration
- Crystal connector integration
- connector execution service
- raw snapshot storage service
- Data Ledger writes

### Sprint 5 — case state

- case CRUD
- findings
- decisions
- evidence links
- running summary support

### Sprint 6 — AI layer

- case context builder
- Foundry client wrapper
- digital colleague definitions
- AI execution logging
- report drafting endpoint

### Sprint 7 — usage and hardening

- usage telemetry
- audit completion
- tests
- deployment workflow
- Bicep templates

***

## Definition of done for each module

A module is only considered complete when:

1. it has a clear responsibility,
2. it is placed in the correct folder,
3. it has typed schemas,
4. it has tests or at minimum testable seams,
5. it logs meaningful actions,
6. it respects tenant scope,
7. it does not duplicate logic from another module,
8. and its data path is explainable.

***

## Specific instructions for Claude Code behavior

When generating code, Claude Code must:

- explain the module it is creating,
- explain why that module belongs where it does,
- avoid changing unrelated modules without reason,
- create code in reviewable increments,
- keep commits small and meaningful,
- prefer explicit service and repository patterns,
- and maintain a running architecture note in the repository.

### Required repository documentation files

Create and maintain:

- `README.md`
- `ARCHITECTURE.md`
- `MODULES.md`
- `DECISIONS.md`

### Purpose of these files

- `README.md` = how to run the project
- `ARCHITECTURE.md` = system overview and layers
- `MODULES.md` = what each backend block does
- `DECISIONS.md` = important architectural choices and why they were made

This makes later review by a senior engineer much easier.

***

## What not to do

Do not let Claude Code:

- generate giant all-in-one files,
- put business logic in route files,
- mix connector and AI logic together,
- rely on implicit hidden state,
- create unlogged background behavior,
- store raw secrets in code or DB,
- attach AI outputs to nothing,
- or use ambiguous service boundaries.

***

## Final instruction

Build Datails as a **modular, auditable, case-centric Operational AI Workspace backend**.

The system must be:

- understandable,
- inspectable,
- traceable,
- cloud-safe,
- and extendable.

Prioritize:

- modularity over speed hacks,
- provenance over convenience,
- explicit service layers over magic,
- and durable operational state over chat transcripts.

The first goal is a real pilot for crypto investigators.
The second goal is a codebase that a future senior engineer can trust, review, and extend without needing to rewrite from scratch.
