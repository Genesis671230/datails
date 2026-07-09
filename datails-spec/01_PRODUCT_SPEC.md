# Datails — Claude Code Build Specification

*(Per LD-21, all `digital_colleague*` names and `/api/v1/digital-colleagues` routes in this document read as `workflow_agent*` / `/api/v1/workflow-agents`.)*

## Purpose

This document is the single source of truth for using Claude Code to build the first working backend for **Datails**, while the frontend is built in Lovable and both are later deployed into your own Azure environment.

This is **not** a generic AI product.
This is **not** a chatbot.
This is **not** a crypto investigation tool that replaces investigators.

Datails is a **pre-built Operational AI Workspace for digital asset investigations and compliance**.

Its core purpose is to give crypto investigators a structured, case-centric, cloud-safe environment where:

- they connect their own tools and data,
- AI assists within operational workflows,
- work is organized around objects and state, not chats,
- outputs are governed, traceable, and reusable,
- and over time their methodology and institutional knowledge compound inside the workspace.

The core product thesis is:

> **The object model — not chat — is the product.**
> Cases, wallets, findings, decisions, reports, connectors, ledgers, and workflows are the product.
> Chat is only one interface into them.

The headline promise is:

> **You never explain your case twice.**
> Open a case and your AI colleagues already know what happened, what data is connected, what has been decided, and what comes next.

***

## Build Strategy

The build happens in three coordinated layers:

### 1. Claude Code builds the backend

Claude Code is used to generate and maintain the backend codebase, infrastructure-as-code, containerization, schema, API layer, and deployment setup.

### 2. Lovable builds the frontend

The frontend UI is created in Lovable, then pushed into GitHub. Lovable is used as a design/scaffolding tool only, not as the runtime or hosting provider.

### 3. Azure is the runtime

The final deployed product runs in your own Azure environment, not in Lovable, not in Claude, and not in any external public AI workspace.

The intended deployment flow is:

```text
Claude Code -> backend repo on GitHub
Lovable -> frontend repo on GitHub
GitHub Actions -> deploy frontend + backend -> Azure
Azure Foundry -> provides models / agents / AI runtime
Azure infrastructure -> provides app runtime, storage, security, secrets, identity
```

Important clarification:

**Azure Foundry is not where the frontend and backend are "hosted together" as a full application platform.**
Foundry is the **AI runtime and orchestration layer**.
Your application still needs normal Azure hosting services around it.

Recommended runtime:

- Frontend: Azure Container Apps or Static Web Apps
- Backend: Azure Container Apps
- Database: Azure Database for PostgreSQL
- Secrets: Azure Key Vault
- Storage: Azure Blob Storage
- API front door: Azure API Management
- Identity: Microsoft Entra ID / Entra External ID
- AI: Azure AI Foundry

***

## Product Definition

Datails v1 is a **pre-built crypto investigation workspace**.
It is not a blank canvas like Claude or Perplexity.
It gives investigators a structured working environment from day one.

### The workspace includes

- **Connect Data**
- **Executive Dashboard**
- **Case Manager**
- **Transaction Explorer**
- **Report Generator**
- **Digital Colleagues**
- **Decision Ledger**
- **Data Ledger**
- **AI Governance**
- **Chat with your connected case data**
- **Basic workflow templates**

### Product design principle

The user should not feel like they are building systems.
They should feel like they entered an investigation operating environment.

This means:

- no blank "start from scratch" workspace,
- no exposed JSON,
- no exposed orchestration graph,
- no requirement to understand agents, MCP internals, or prompt routing,
- no conversation-centric experience.

The product should feel more like:

- Salesforce for opportunities,
- ServiceNow for tickets,
- but for crypto investigation cases.

***

## What the backend must do

The backend is responsible for six things:

### 1. Multi-tenant workspace foundation

Each customer gets a tenant-scoped workspace.
The workspace is the top-level container for all cases, connectors, methodology, reports, and usage.

### 2. Operational object model

The backend stores and manages the structured entities that make the product operational.
These objects are the product.

### 3. AI runtime integration

The backend connects to Azure AI Foundry for model access, agent execution, summarization, report drafting, and scoped assistant functionality.

### 4. Connector integration layer

The backend manages external data and tool connections using API connectors and MCP-compatible patterns where relevant.

### 5. Provenance, governance, and audit baseline

The backend logs all meaningful system actions so outputs can later be made auditable, reviewable, and enterprise-ready.

### 6. Usage and commercial control

The backend meters usage and supports the free-to-paid motion.
In Phase 1, Azure credits fund initial usage.
Later this evolves into platform billing.

***

## Phase 1 Scope

The first build is a **lean but real pilot environment**.
It is not the final enterprise architecture.
It is the smallest architecture that proves the product thesis with real investigators.

### In scope

- Tenant/workspace creation
- User authentication
- Onboarding flow support
- Methodology capture
- Connector registry
- Case manager backend
- Findings and decision objects
- Transaction explorer support using Crystal data
- Report generation support
- Digital colleague execution support
- Decision Ledger
- Data Ledger
- AI call logging
- Usage metering
- Azure Foundry integration
- GitHub-based deployment
- Containerized backend

### Out of scope for Phase 1

- Deep ontology engine
- Advanced deep-data-modelling engine
- Marketplace
- Full no-code workflow builder
- Sovereign/on-prem client deployment automation
- Full confidential computing implementation
- Full enterprise RBAC matrix
- Multi-party coordination network
- Advanced autonomous tracing
- Complex graph intelligence engine

These may come later, but must **not** block Phase 1.

***

## Core Backend Architecture

### Core principle

The backend is not chat-first.
It is **object-first**.
Every AI interaction must attach to a real object context where possible.

Primary object domains:

- Tenant
- User
- Workspace
- Methodology
- Connector
- Case
- Finding
- Decision
- Report
- Data Ledger Entry
- Decision Ledger Entry
- AI Call Log
- Usage Record

### Recommended stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x async
- Alembic
- PostgreSQL
- Azure Key Vault SDK
- Azure Identity SDK
- Azure AI Foundry SDK / Azure OpenAI compatible APIs where appropriate
- Docker
- GitHub Actions
- Bicep for infrastructure

***

## Recommended Repository Structure

```text
datails/
  backend/
    app/
      api/v1/
      core/
      db/
      services/
      models/
      schemas/
      middleware/
      integrations/
      workers/
      main.py
    alembic/
    tests/
    Dockerfile
    requirements.txt
  frontend/
    (Lovable-generated code)
  infra/
    bicep/
  .github/
    workflows/
  docker-compose.yml
  README.md
```

*(Note: the canonical repository tree is defined in `03_IMPLEMENTATION_PLAN.md` and locked by LD-2 in `04_ERRATA_LOCKED_DECISIONS.md`.)*

***

## Backend Functional Domains

## 1. Identity and Workspace

### Required functionality

- Create tenant
- Create workspace
- Associate users to tenant/workspace
- Support initial onboarding state
- Store basic tenant plan / trial state

### Required tables

- tenants
- users
- workspaces
- onboarding_sessions

### Minimum behavior

When a user signs up:

1. a tenant is created,
2. a default crypto-investigation workspace is created,
3. onboarding begins,
4. the user is guided through connecting data and teaching methodology.

***

## 2. Methodology Capture

This is a critical part of the moat.
The workspace should adapt around the investigator's way of working.

### During onboarding capture:

- specialty / type of investigations,
- trusted tools,
- preferred jurisdictions,
- preferred report structures,
- preferred exchanges / communication templates,
- workflow steps they usually follow,
- what they want AI to assist with.

### Required tables

- methodologies
- methodology_steps
- generated_templates
- digital_colleague_profiles

### Output of methodology capture

The backend should persist enough structure to later:

- generate report templates,
- initialize digital colleagues,
- seed future workflow templates,
- and eventually support a marketplace.

This data must **not** be stored as unstructured text only.
It must be stored in a structured way that can evolve later.

***

## 3. Connector Layer

The workspace must connect to the customer's own tools and data.
Customers bring their own licenses and API keys.

### Connector types in Phase 1

- Crystal (see LD-16 in `04_ERRATA_LOCKED_DECISIONS.md` for the corrected connector definition)
- One generic BYO API connector
- File upload / ingest support

### Future connector types

- TRM
- Arkham
- Elliptic
- Merkle Science
- Slack
- Email
- Databases
- MCP server-based tools

### Required connector behavior

- store connector metadata,
- store auth type,
- store secret reference only,
- never store raw secrets in database,
- retrieve secrets from Azure Key Vault,
- enforce daily call ceilings,
- snapshot retrieved data into ledger/storage.

### Required tables

- connectors
- connector_runs
- connector_credentials_refs

***

## 4. Case-Centric Object Model

This is the heart of the product.

### Required objects

- cases
- case_wallets
- evidence_items
- findings
- decisions
- reports

### Cases must support

- title / type / priority / status
- associated wallets
- associated evidence
- running summary
- related findings
- related reports
- linked decisions
- full context snapshot for AI retrieval

### Important rule

Every important AI interaction should be case-attached whenever possible.
This is what makes the product stateful and useful.

***

## 5. Transaction Explorer Support

The Transaction Explorer is **assisted and human-led**.
It is not autonomous tracing.

### Phase 1 behavior

- pull Crystal-based transaction/context results,
- display/store trace-relevant data,
- support investigator-guided FIFO exploration,
- let the system summarize what has been discovered,
- let findings be created from trace exploration,
- require human confirmation before durable action is committed.

### Guardrail rule

The system can assist, summarize, suggest, and draft.
It cannot silently create authoritative trace outcomes without human oversight.

***

## 6. Report Generator

This is a major value surface and one of the fastest ROI features.

### Reports to support in Phase 1

- police intake report,
- exchange compliance request,
- investigator summary,
- basic structured dossier.

### Report generation behavior

- use case data + findings + connected evidence,
- use methodology-informed template structure,
- generate draft only,
- require human review before export/finalization,
- store versions.

### Required tables

- reports
- report_versions
- report_templates

***

## 7. Digital Colleagues

These are named operational AI assistants embedded into the workspace.
They are not generic chatbots.

### Initial digital colleagues

- Intake Analyst
- Report Writer
- Compliance Analyst
- Research Analyst

### Required behavior

- each has a defined role,
- each has scoped allowed actions,
- each has access boundaries,
- each is grounded in workspace/case context,
- outputs can be approved, rejected, or revised,
- no colleague can execute real-world action without a human gate.

### Required tables

- digital_colleagues
- digital_colleague_runs
- digital_colleague_permissions

***

## 8. Decision Ledger and Data Ledger

These are essential.
They create provenance and future defensibility.

### Data Ledger stores

- what external/source data was retrieved,
- where it came from,
- when it was retrieved,
- under which connector,
- hash/reference to raw payload,
- storage reference.

### Decision Ledger stores

- what was decided,
- by whom,
- based on which findings or data,
- at what time,
- whether AI-assisted,
- whether approved.

### Required tables

- data_ledger
- decision_ledger

These ledgers should be append-only in practice.

***

## 9. AI Runtime via Azure Foundry

Azure Foundry is the AI runtime layer.
It is not the whole product.

### Use Foundry for

- model access,
- prompt execution,
- hosted/prompt agents where useful,
- case summarization,
- report drafting,
- structured extraction,
- assistant responses,
- model governance/logging where supported.

### Phase 1 AI rules

- prefer Azure-hosted models only,
- no public/open model endpoints,
- no sending sensitive investigator data to consumer AI tools,
- keep context tightly scoped,
- cache case context for reuse,
- use cheaper models for formatting-heavy work,
- use stronger reasoning models only when needed.

### AI call logging required

Every AI call should log:

- tenant_id
- workspace_id
- case_id if applicable
- digital colleague if applicable
- task type
- model used
- latency
- token usage if available
- prompt hash
- response hash
- created_at

### Required tables

- ai_call_log
- ai_task_runs

***

## 10. Usage and Trial Logic

Phase 1 commercial logic is simple.
Initial use is funded by Azure credits.
The product still needs usage telemetry.

### Required capabilities

- meter tenant usage,
- attribute usage to major action type,
- track trial status,
- support soft/hard gating later,
- make upgrade paths possible later.

### Required tables

- usage_records
- tenant_plan_state

Do not build full billing first.
Just build proper usage accounting.

***

## Security and Cloud-Safe Requirements

These are non-negotiable.

### 1. Azure-only runtime

Production runtime is in your Azure environment.

### 2. No public AI tool dependency in production

No runtime dependency on Claude web, Perplexity, Cursor, ChatGPT consumer, or external public model endpoints.

### 3. Key Vault for all secrets

Connector keys, DB secrets, app secrets must be stored in Key Vault.

### 4. Tenant isolation from day one

Every customer-facing record must be tenant-scoped.

### 5. Human approval for high-trust actions

No AI-only finalization of important outputs.

### 6. Source-cited outputs where relevant

Reports and AI outputs should retain source references where possible.

***

## Deployment Model

### Frontend

Lovable-generated frontend code is pushed to GitHub.
You deploy it yourself into Azure.

Recommended:

- Azure Container Apps, or
- Azure Static Web Apps if architecture supports it.

### Backend

Claude Code generates the backend.
You push the backend repo to GitHub.
Deploy into Azure Container Apps.

### AI Runtime

Backend integrates with Azure Foundry.
Azure Foundry does not replace the backend.
It supplies models/agents.

### CI/CD

Use GitHub Actions.

Recommended flow:

- push frontend to GitHub,
- push backend to GitHub,
- deploy both into Azure,
- backend reads config and secrets from Key Vault,
- backend connects to Foundry.

**Frontend and backend come together in your Azure environment**, and the backend then connects to Azure Foundry as the AI layer.

***

## What Claude Code Should Build First

Claude Code should build in this order:

### Step 1 — Backend scaffold

- FastAPI app
- folder structure
- config system
- Dockerfile
- Docker Compose
- health endpoint

### Step 2 — Database foundation

- SQLAlchemy models
- Alembic migrations
- base tenant/workspace/user schema

### Step 3 — Auth and workspace flow

- auth integration placeholder / middleware *(superseded by LD-1: Entra External ID JWT validation from day one)*
- create tenant/workspace/user records
- onboarding session support

### Step 4 — Methodology capture

- schema
- endpoints
- persistence

### Step 5 — Connector layer

- Crystal connector
- generic BYO API connector
- Key Vault secret resolution
- connector test endpoint

### Step 6 — Case domain

- CRUD for cases
- findings
- decisions
- evidence
- running summary support

### Step 7 — Ledger domain

- data ledger
- decision ledger
- append-only patterns

### Step 8 — Foundry integration

- case-aware assistant endpoint
- digital colleague run endpoint
- report drafting endpoint
- AI call logging

### Step 9 — Usage telemetry

- usage record creation
- tenant usage summary endpoint

### Step 10 — Production readiness baseline

- containerization finalization
- environment variable setup
- GitHub Actions
- Bicep infra templates

***

## API Surface — Initial Version

Suggested initial route structure:

```text
/api/v1/auth
/api/v1/tenants
/api/v1/workspaces
/api/v1/onboarding
/api/v1/methodologies
/api/v1/connectors
/api/v1/cases
/api/v1/findings
/api/v1/decisions
/api/v1/reports
/api/v1/digital-colleagues
/api/v1/ledger/data
/api/v1/ledger/decision
/api/v1/ai
/api/v1/usage
/api/v1/health
```

*(Note: the exact endpoint list is defined in `03_IMPLEMENTATION_PLAN.md` as amended by LD-1 and LD-8.)*

***

## What Not To Build Yet

Claude Code must avoid these traps in the first phase:

- do not build a generic workflow-builder product,
- do not build a giant ontology system first,
- do not build a broad horizontal SaaS platform first,
- do not build a consumer chatbot,
- do not build 20 connectors,
- do not build complex billing,
- do not build on-prem automation first,
- do not try to automate investigator judgment.

The goal is a **lean but serious pilot environment** for crypto investigators.

***

## Success Criteria for Phase 1

The Phase 1 backend is successful when the following is true:

1. A user can sign up and get a tenant-scoped crypto-investigation workspace.
2. The onboarding flow captures their methodology and stores it structurally.
3. They can connect Crystal and one additional BYO connector securely.
4. They can create and manage cases.
5. A case can accumulate evidence, findings, decisions, and reports.
6. A digital colleague can generate useful draft output grounded in case context.
7. Data retrieval and decisions are recorded in the ledgers.
8. AI calls are logged.
9. Usage is metered.
10. Frontend and backend are both deployable from GitHub into your Azure environment and the backend successfully calls Azure Foundry.

***

## Final instruction for Claude Code

Build the backend as the foundation for a **case-centric Operational AI Workspace for crypto investigators**, deployed in Azure, with Azure Foundry as the AI runtime, Lovable as the frontend design source, and GitHub as the source of truth.

Do not optimize for genericity.
Do not optimize for theoretical future enterprise scale at the expense of speed.

Optimize for:

- clean architecture,
- extension into the future,
- secure Azure-native runtime,
- object-centric workflows,
- and a real pilot that users can use.
