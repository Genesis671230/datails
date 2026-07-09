# Datails — Errata and Locked Decisions (v3)

## Status of this document

This file is **canonical and binding**. It amends the three core specification documents:

1. `01_PRODUCT_SPEC.md`
2. `02_ARCHITECTURE_SPEC.md`
3. `03_IMPLEMENTATION_PLAN.md`

Where this document conflicts with any of the three, **this document wins**. Claude Code must not re-open, reinterpret, or "improve" any decision locked here. If a locked decision proves impossible during implementation, stop and raise it — do not substitute a convenience alternative.

v2 added LD-13 – LD-17 (evidence-driven, from the Operator Intelligence KB) and updated the LD-6 spike scope. v3 adds LD-21 – LD-30, reconciling the package with the **Foundation — AI Workspace v7.0** document set (canonical narrative) and founder decisions of 9 July 2026. Citation IDs like [03-12] refer to `Transcripts/Operator_Intelligence_KB/15_transcript_index/`.

***

## LD-1 — Authentication and identity

**Decision: Microsoft Entra External ID with Entra-issued JWT validation, from day one. No auth stub in any deployed environment.**

- The frontend obtains tokens from Entra External ID. The backend validates Entra-issued JWTs (signature, issuer, audience, expiry) in middleware on every request except `/api/v1/health`.
- `users.external_auth_id` stores the Entra object ID (`oid` claim). On first authenticated request from an unknown `oid`, the signup/bootstrap flow creates tenant → user → default workspace.
- Tenant resolution: the validated token maps to exactly one user row, which carries `tenant_id`. Tenant context is derived **only** from the authenticated identity — never from request bodies, query params, or headers supplied by the client.
- A local-development bypass is permitted **only** behind an explicit `AUTH_DEV_MODE=true` env flag, which must hard-fail if the environment is not `local`. It must never be deployable to Azure.
- This inserts a new **Phase 2A — Auth middleware** into the implementation plan, immediately after Phase 2 tables and before any business route is built. The endpoint list gains no `/auth` routes in Phase 1: Entra handles login; the backend only validates.
- Provisioning trigger: tenant/user/workspace creation for an unknown `oid` happens only via `POST /api/v1/workspaces/bootstrap` (called by the frontend after first login) — not implicitly in middleware on arbitrary routes.

**Checkpoint addition:** Phase 2 is not complete until a request with a valid Entra JWT resolves to a tenant/workspace context and a request without one is rejected with 401.

***

## LD-2 — Canonical repository structure

**Decision: the repository tree in `03_IMPLEMENTATION_PLAN.md` is the single canonical structure.** It supersedes the trees in files 01 and 02.

- There is exactly **one** ledger module location: `services/ledgers/`. No standalone `app/ledgers/` directory.
- Migrations live in `alembic/` only. There is no `db/migrations/`.
- `tests/` lives at `backend/app/tests/`.
- **No background workers in Phase 1.** Connector runs and AI tasks execute synchronously in the request path, with sensible timeouts. This is a deliberate pilot-scale decision and must be recorded in `DECISIONS.md`. No `workers/` directory until a real need arrives.

***

## LD-3 — Ledger integrity enforcement

**Decision: database-level insert-only enforcement now; hash chaining deferred.**

- The tables `data_ledger`, `decision_ledger`, and `ai_call_log` are append-only, enforced in the database, not by convention:
  - the application database role is granted `INSERT` and `SELECT` only (no `UPDATE`, no `DELETE`) on these tables, **and**
  - a trigger on each table raises an exception on `UPDATE` or `DELETE` as defense in depth.
- Both mechanisms are created in the same Alembic migration that creates the tables.
- Cross-entry hash chaining is explicitly deferred; record the deferral and rationale in `DECISIONS.md`. Per-entry `payload_hash` (SHA-256) is still mandatory now.

***

## LD-4 — Connector ingestion atomicity

**Decision: blob first, ledger second, single DB transaction for the durable record. No ledger entry may exist without its payload.**

Canonical ingestion sequence:

1. Resolve secret from Key Vault.
2. Execute external call.
3. Write raw payload to Blob Storage; compute SHA-256 of the payload.
4. In **one database transaction**: write the `data_ledger` entry (with `storage_ref` and `payload_hash`) and update the `connector_run` to `completed`.

Failure semantics:

- External call fails → `connector_run` marked `failed` with `error_message`. No blob, no ledger entry.
- Blob write fails → `connector_run` marked `failed`. No ledger entry.
- Ledger transaction fails after blob write → `connector_run` marked `failed`; the orphaned blob is acceptable and cleaned by a periodic reaper later. **An orphaned blob is tolerable; a ledger entry pointing at nothing is not.**

***

## LD-5 — Case context builder rules

**Decision: fixed inclusion rules, explicit token budget, defined staleness policy.**

- Default context budget: **8,000 tokens**, configurable per task type in `services/ai/model_router.py` config. Never unbounded.
- Fixed inclusion priority (truncate from the bottom when over budget):
  1. Case core: title, type, status, running summary
  2. Approved findings (newest first)
  3. Decisions (newest first)
  4. Wallets with labels (labels include provenance refs, per LD-14 / `05_DOMAIN_MODEL.md` §5)
  5. Evidence references (references and titles, never full raw payloads)
  6. Methodology cues relevant to the task type and case_type
  7. Unapproved / draft findings
- Raw connector payloads are **never** inlined into context; only their normalized subsets and `data_ledger` references.
- Every context assembly emits the list of source references used, so AI outputs can cite them.
- Staleness: context is rebuilt on any write to the case or its child objects; otherwise a cached context may be reused for up to **15 minutes**. Cache key: `case_id + max(updated_at across case graph)`.
- The context builder is one service (`services/ai/context_builder.py`). No route, agent, or report service may assemble case context independently.

***

## LD-6 — Crystal API spike before Phase 8 (scope updated in v2)

**Decision: a timeboxed spike (max 2 days) against the real Crystal API is a mandatory gate before the connector is designed.**

Already answered first-party by Crystal [03-12] — do not re-derive, do verify:

- no external visualization API (Graphene internal-only); all transaction/transfer/entity data retrievable via API; Risk Check API (fast) vs deep calls (slow); standard partner starter set of 3–4 endpoints; no direct DB access; test-account process via Crystal contacts (Joey, Yasek); NDA via Crystal legal; KYC of end customers mandatory.

The spike must still establish and document in `integrations/crystal/CRYSTAL_NOTES.md`:

- authentication mechanism and key handling,
- the exact endpoints in the starter set and their payload shapes,
- rate limits and quota behavior,
- pagination and response shapes for wallet lookup,
- error formats,
- pricing/commercial terms if disclosed,
- **whether persisting raw Crystal payloads in tenant Blob Storage and embedding derived data in third-party-facing reports is permitted under Crystal's licensing** (this affects LD-4 and the Report Generator),
- **blockchain-explorer connector vendor selection** (see LD-15): pick the vendor, confirm free-tier limits and payload shapes.

Phase 8 route contracts are **provisional until the spike completes** and must be adjusted to observed reality, not assumption.

***

## LD-7 — Phase ordering fix (blob before ledgers)

**Decision: Phases 6 and 7 of the implementation plan are swapped** (already applied in `03_IMPLEMENTATION_PLAN.md` v2 numbering):

- **Phase 6 — Blob storage snapshots**: Blob client wrapper, serializer/hash utility, snapshot write path.
- **Phase 7 — Data Ledger, Decision Ledger, AI Call Log**: ledger tables, insert-only enforcement (LD-3), writer services, read endpoints (LD-8).
- The checkpoint "connector data can be written to storage and logged" belongs to Phase 7, when both capabilities exist.

***

## LD-8 — Ledger read endpoints

**Decision: provenance must be visible in the pilot, not just stored.**

```text
GET /api/v1/ledger/data?case_id=&connector_id=&limit=&offset=
GET /api/v1/ledger/decision?case_id=&limit=&offset=
```

- Tenant-scoped, read-only, newest first. Built in Phase 7 alongside the writers.
- Additionally, `GET /api/v1/cases/{id}` must explicitly return the case's findings and decisions (current objects), so the Phase 5 checkpoint "coherent state" is testable rather than interpretive.

***

## LD-9 — Decisions table vs. Decision Ledger: source of truth

**Decision: `decisions` holds the current decision objects; `decision_ledger` is the immutable event history. They are not alternatives — every decision write emits a ledger event.**

- Create/update/approve/supersede on a decision **must**, in the same database transaction, append a `decision_ledger` event (`event_type` = `created`, `approved`, `superseded`, etc.) referencing the `decision_id`.
- Decisions are never hard-deleted; a changed decision is superseded by a new decision row plus a ledger event.
- Queries about "what is decided now" read `decisions`. Queries about "how did we get here" read `decision_ledger`.
- This rule goes verbatim into `DECISIONS.md`.

***

## LD-10 — Tests are part of every phase gate

**Decision: no phase checkpoint passes without tests.** Appended to every phase checkpoint in the implementation plan:

- unit tests for each new service (happy path + at least one failure path),
- one integration test per new route surface (against a test database),
- tenant-isolation test wherever a new tenant-scoped table is introduced (tenant A must never read tenant B's rows),
- CI (GitHub Actions) green before the phase is marked complete in `IMPLEMENTATION_STATUS.md`.

Phase-specific minimums:

- Phase 2A: valid JWT accepted, invalid/missing JWT rejected, cross-tenant access rejected.
- Phase 7: `UPDATE`/`DELETE` attempts on ledger tables fail at the database level.
- Phase 12: report versioning produces immutable prior versions.

***

## LD-11 — Connector call-limit accounting

**Decision: drop the `calls_today` counter and its reset logic from the `connectors` table.**

- Daily usage is **derived** by counting `connector_runs` for the connector within the current UTC day. This is race-free and requires no reset job.
- `daily_call_limit` remains as configuration on `connectors`.
- Enforcement happens in the connector execution service before the external call is made.

***

## LD-12 — Document hygiene for the canonical spec set

**Decision: the canonical spec files in the repository must contain specification content only.**

- No conversational/assistant postambles or citation fragments.
- No external file links — especially pre-signed URLs containing credentials/tokens.
- The canonical set is exactly the eight files in this `datails-spec/` folder. Everything else is working material, not spec.

***

## LD-13 — Wallets are workspace-global (v2, evidence-driven)

**Decision: wallets are workspace-scoped entities; cases reference them through a join table.**

- Rationale: criminal organizations reuse wallet infrastructure across cases; a wallet observed in one case must surface when it appears in another [02-16].
- Canonical schema: `wallets` + `case_wallets` join in `05_DOMAIN_MODEL.md` §1.1. This replaces the originally planned case-scoped wallet design.
- `wallets.is_watched` ships as a schema hook only; no monitoring behavior in Phase 1.

***

## LD-14 — Wallet labels carry provenance (v2, evidence-driven)

**Decision: no bare label strings. Labels live in `wallet_labels` with source, connector, `data_ledger_ref`, and observation timestamp.**

- Rationale: entity labeling is the core vendor IP and the pivotal investigative fact ("by knowing that this is Binance, I know to whom I should speak" [02-16]); for court-facing defensibility a label must be traceable to its retrieval.
- Labels are append-only in practice: newer observations are new rows; "current" = latest by `observed_at`.
- Canonical schema: `05_DOMAIN_MODEL.md` §1.2.

***

## LD-15 — Blockchain-explorer connector instantiates the generic BYO connector (v2)

**Decision: the "one generic BYO API connector" of Phase 1 is built as an Etherscan-class public blockchain-explorer connector.**

- Primary job: wallet-address validation at intake + base transaction data [02-16].
- Publicly documented API, customer-supplied key, generous free tier.
- **No vendor docs are currently in hand.** Vendor selection, free-tier verification, and payload-shape confirmation are part of the LD-6 spike. Until then: build the generic connector base class against a mock; do not hard-code any vendor's payload shapes.

***

## LD-16 — Crystal connector correction (v2, evidence-driven)

**Decision: remove "Crystal Tier 1 / Crystal Tier 2" everywhere. No such API tiering exists** (Crystal first-party [03-12]; "tier two" in that conversation refers to target customers, not APIs).

- The connector is designed around the observed surface: data endpoints (full entity/transaction retrievability), the fast **Risk Check API** vs heavier deep calls, and a 3–4 endpoint partner starter set. Details: `05_DOMAIN_MODEL.md` §4.1.
- No visualization API exists; Datails builds its own node-based visualization on API data.
- **Crystal requires KYC of Datails end customers.** In the pilot this is an administrative obligation at tenant onboarding (manual is acceptable); record it in `DECISIONS.md`. Schema impact: none in Phase 1 beyond a tenant metadata flag.
- Do not encode "tier" concepts into `connector_type`, schema, or code.

***

## LD-17 — Freeze/blocklist request is a first-class report type (v2, evidence-driven)

**Decision: `freeze_blocklist_request` joins the Phase 12 report-type enum**, together with the also-new `sar_draft` (both defined in `05_DOMAIN_MODEL.md` §1.4).

- Rationale: the per-platform, per-jurisdiction freeze letter with transaction hashes is the most automatable high-value output in the discovery corpus [02-16], [02-19]; it was previously hiding inside "exchange compliance request."
- Always generated as draft, always behind a human approval gate (it is a legal-weight communication).
- Reality note for prompts/UX: exchanges act on law-enforcement requests; a private investigator's letter is a notification that prepares the LE handoff, not an order [02-16]. The template wording must reflect this.

***

## LD-18 — Build-order reconciliations (v2.1, from consistency audit)

**Decision: cross-phase dependencies are resolved as follows.**

1. **LD-9 takes effect at Phase 7.** Decisions created in Phases 5–6 exist without ledger events; the Phase 7 migration **backfills** a `created` event for every pre-existing decision row. From Phase 7 onward, the same-transaction rule is absolute.
2. **LD-4 full sequence applies from Phase 7 onward.** The Phase 4 connector test call is exempt: it must not persist durable data (no blob, no ledger) — it only verifies secret resolution and connectivity. The master-prompt hard-stop check "every connector run follows LD-4" is scoped to phases where Blob Storage and the Data Ledger exist.
3. **`services/ai/model_router.py` is created in Phase 9** as a configuration module (context budgets per task type, per LD-5); the task-executor wiring is added in Phase 10. LD-5's reference points at this config module.
4. **`wallet_labels.data_ledger_id`** exists as a nullable column from the Phase 5 migration; its FK constraint to `data_ledger` is added in the Phase 7 migration. From Phase 8 onward, connector-sourced labels must populate it.

***

## LD-19 — Schema supersessions and completions (v2.1)

**Decision: the following tables named in `01_PRODUCT_SPEC.md` are superseded and must NOT be created:**

- `ai_task_runs` → covered by `ai_call_log` + `digital_colleague_runs`.
- `connector_credentials_refs` → superseded by the `secret_ref` column on `connectors`.
- `digital_colleague_permissions` → superseded by `allowed_tools_json` / `allowed_actions_json` on `digital_colleagues`.
- `report_templates` → report templates are stored in `generated_templates` (Phase 3), which serves both methodology-generated and report templates; add a nullable `jurisdiction_variants_json` column to `generated_templates` to hold the LD-17/`05_DOMAIN_MODEL.md` §1.5 wording overlays.

**Also decided:** `methodologies.version` (integer column) is sufficient versioning for Phase 1 — no `methodology_versions` table (record in `DECISIONS.md`). `connector_type` value `generic_api` denotes the connector base class used for mocks/tests only; Phase 1 registrable types are `crystal`, `blockchain_explorer`, `file_upload`.

***

## LD-20 — Case-aware assistant endpoint (v2.1)

**Decision: Phase 10 exposes one AI route:**

```text
POST /api/v1/ai/assistant
```

Body: `case_id` (required), `task_type` (one of the Phase 10 task types), `input` (user query/instruction). Behavior: resolve tenant → build case context via the context builder (LD-5) → execute through the Foundry wrapper → log to `ai_call_log` → return draft output with source references. This is the "chat with your connected case data" surface; it is case-attached by construction. Added to the canonical endpoint list.

***

## LD-21 — Foundation v7.0 alignment and terminology (v3)

**Decision: the Foundation — AI Workspace v7.0 document set is the canonical narrative. In code and technical docs, the agents are `workflow_agents`.**

- Rename throughout: `digital_colleagues` → `workflow_agents`, `digital_colleague_runs` → `workflow_agent_runs`, `digital_colleague_profiles` → `workflow_agent_profiles`, `colleague_type` → `agent_type`, routes `/api/v1/digital-colleagues` → `/api/v1/workflow-agents`. "Digital Colleagues" (aka "AI agents") is the external, non-technical register only (founder ruling, 7 Jul 2026).
- v7.0 additions the package must honor: **Learning Layer schema from day one, capture wired from Slice 2** (LD-30), **case memory as a named acceptance test** (07_BUILD_PLAN), the fund-flow trace model with per-hop confidence (`05_DOMAIN_MODEL.md` §8), and the invisible fair-use posture (`tenants.credit_limit_usd` backstop — schema hook now, HTTP 402 behavior deferred to BACKLOG).
- Deferred v7 items recorded in BACKLOG.md at Slice 0: deterministic risk-rule engine, entity registry (lite), CrimeTrace ingestion endpoint, credit backstop behavior, UAE North stamp, MCP connectors, Redis cache (LD-5 cache is in-process for the pilot).

***

## LD-22 — Crystal credentials and connector modes (v3)

**Decision: pilot uses a Datails-provided shared temporary Crystal key; the schema supports per-tenant BYO from day one; "Tier 1 / Tier 2" are Datails connector modes, not Crystal API claims.**

- `connectors.credential_owner`: `datails_shared | tenant`. Pilot Crystal connector = `datails_shared`, key in Key Vault. Future: investigators bring their own API keys or MCP connectors (`mcp_server` reserved in `connector_type`, not built).
- **Shared-key arbitration:** `daily_call_limit` is per-connector (per-tenant); a **global daily budget for the shared key** is enforced additionally in the connector execution service, so one cohort member cannot starve the others.
- **Key rotation:** the temp key will expire; rotation = Key Vault secret version swap, zero code change. Write the procedure into the runbook (LD-29).
- **Connector modes** (refines LD-16's wording, keeps its substance): the Crystal connector exposes two Datails-side modes — `risk_check` ("Tier 1", fast, maps to Crystal's Risk Check API) and `full_investigation` ("Tier 2", deep calls). These are Datails product terms per Foundation v7.0; they make no claim about Crystal's own API tiering [03-12].

***

## LD-23 — Region strategy (v3)

**Decision: one pilot stamp in Azure West Europe; region is a Bicep parameter; multi-region = additional stamps with per-tenant assignment, later.**

- Rationale: founding cohort and their data subjects are European (court-facing story), broader Foundry model availability. DIFC compliance attaches to Datails' Dubai operations, not to hosting location; record this reasoning in `DECISIONS.md`.
- The full stack (Postgres, Blob, Key Vault, Foundry endpoint, Container Apps) deploys as one self-contained regional stamp. A UAE North stamp is a later deployment of the same templates (BACKLOG).
- **Day-one verification:** GPT-4o and GPT-4o-mini deployment availability and quota in West Europe before Slice 2. This supersedes the "UAE North" constraint in the Foundation set for the pilot stamp (founder decision, 9 Jul 2026).

***

## LD-24 — Inference: initial pair + governed multi-model rule (v3)

**Decision: initial stack is GPT-4o (reasoning) and GPT-4o-mini (formatting) via Azure AI Foundry in the pilot region. Additional models are welcome behind the same abstraction.**

- A model may be added only if it is deployed through the Datails Foundry instance in the tenant's region (governed, region-bound, logged). **Never an external or ungoverned endpoint.**
- Adding a model = a `model_router` config entry (task types routed to it, cost/latency notes) + a `DECISIONS.md` line. No code change elsewhere; `ai_call_log.model_name` already captures which model served each call.

***

## LD-25 — Runtime: Azure Container Apps (v3)

**Decision: v0 deploys to Azure Container Apps, not AKS.**

- Rationale: days-to-live timeline; ACA revision-based rollback; same Docker containers move to AKS later if enterprise deployment demands it. This deviates from the signed sprint document's AKS Bicep (founder has taken over the build, 9 Jul 2026) — record the deviation in `DECISIONS.md`.

***

## LD-26 — Build order: slices supersede phases; documentation rhythm (v3)

**Decision: `07_BUILD_PLAN.md` (four slices) is the authoritative build order. The 15-phase plan in `03_IMPLEMENTATION_PLAN.md` remains the authoritative *content* reference (tables, routes, rules) but no longer dictates sequence.**

- All LD build-order reconciliations (LD-18) map onto slices as stated in 07.
- **Per-slice documentation:** at every slice boundary Claude Code writes `docs/build-log/<date>-<slice>.md` (what was built: endpoints, tables, decisions, test status, how to verify) and appends any deferred item to a living `BACKLOG.md` with a reason, at the moment of deferral.
- **Frontend contract:** the backend publishes its OpenAPI spec from Slice 0 onward; it is the contract for the frontend build (Lovable is UX design source only — its exported code seeds the frontend repo; nothing is wired from Lovable at runtime). The Entra PKCE login flow is tested with a real token before any frontend integration work.

***

## LD-27 — Workflow-agent runs are resumable state machines (v3)

**Decision: `workflow_agent_runs.status` ∈ `pending | running | awaiting_confirmation | completed | failed | abandoned`, with resume-from-last-confirmed-step.**

- A trace run interrupted by a connector error (429/5xx), a Foundry timeout, or the investigator closing the session resumes from the last **confirmed** hop — never re-executes confirmed work, never silently retries an unconfirmed proposal.
- Every state transition is recorded (timestamp + cause). Runs stuck in `awaiting_confirmation` have no timeout — human pace is the design; runs stuck in `running` time out to `failed` with a resumable checkpoint.

***

## LD-28 — Idempotency on expensive POSTs (v3)

**Decision: POST endpoints that trigger external calls or AI spend require an `Idempotency-Key` header** (connector runs, workflow-agent runs, report drafts, assistant calls).

- Implementation: `idempotency_keys` table (key, tenant_id, route, request_hash, response_ref, created_at; unique on tenant_id+key). Replay returns the original response; conflicting payload under the same key returns 409.

***

## LD-29 — Operational resilience baseline (v3)

**Decision: the following are Slice 0/deploy requirements, not post-pilot hardening.**

- **Backups:** PostgreSQL point-in-time recovery enabled; Blob soft-delete + versioning on. Both in the Bicep from the first deployment — the ledgers are the trust story.
- **Observability:** Application Insights wired (request traces + failed Foundry/Crystal call queries); Azure budget alert on token/credit spend.
- **Runbook:** `docs/RUNBOOK.md` — ACA revision rollback command, Crystal key rotation procedure (LD-22), what to check when the demo breaks.
- **Golden-set smoke test:** 3–5 fixed cases with expected report-draft properties, run on any prompt or model-routing change.
- **Staging:** a second Container Apps revision/environment suffices for the pilot; unfinished surfaces ship behind "coming soon" flags, never half-broken.

***

## LD-30 — Learning Layer: day-one capture, consent-gated (v3)

**Decision: append-only `learning_events` capture starts in Slice 2; capture only, no analytics in the pilot.**

- Captured: recommendation accepted/rejected, report edits, draft approved/rejected, investigator overrides, workflow completion, connector usage, durations (schema: `05_DOMAIN_MODEL.md` §9).
- **Consent enforcement:** `tenants.learning_capture_enabled` (default **false**) checked at the capture point; set true only when the cohort member's Data & Methodology Permission (Foundation doc 06) is signed. Capturing without the flag is a defect, not a shortcut.
- Same insert-only DB enforcement as the other ledgers (LD-3).
- **Tenancy stance reaffirmed:** LD-1 enforcement and LD-10 isolation tests stay from day one, deliberately stricter than the pilot scope's "enforcement post-pilot" — cheap insurance, already built into the plan.

***

## Summary of implementation-plan deltas (v1 + v2; v3 deltas live in LD-21 – LD-30 and `07_BUILD_PLAN.md`)

| Item | Change |
|---|---|
| New Phase 2A | Entra JWT validation middleware, before any business routes (LD-1) |
| Phases 6 ↔ 7 | Swapped: blob storage before ledgers (LD-7) |
| Endpoint list | + 2 ledger read endpoints (LD-8); no `/auth` routes (LD-1) |
| `connectors` table | Remove `calls_today`; derive from `connector_runs` (LD-11) |
| All phase checkpoints | + test requirements (LD-10) |
| Pre-Phase 8 | Mandatory Crystal API spike gate, scope incl. licensing + explorer vendor (LD-6) |
| Ledger migrations | Insert-only grants + triggers (LD-3) |
| Phase 5 wallet schema | `wallets` + `case_wallets` join + `wallet_labels` (LD-13, LD-14) |
| Phase 5 enums | case_type, evidence_type, decision_type per `05_DOMAIN_MODEL.md` §1.3 |
| Phase 3 seed | Baseline methodology seed data per `05_DOMAIN_MODEL.md` §2 |
| Phase 8 connector | Crystal surface corrected, no tiers (LD-16) |
| Generic connector | Instantiated as blockchain-explorer connector, vendor TBD in spike (LD-15) |
| Phase 12 report types | + `freeze_blocklist_request`, `sar_draft` (LD-17) |

***

## Final instruction

These decisions are **locked**. Claude Code builds within them. Any gap not covered by the eight spec files is resolved by the priorities already stated: modularity over speed, provenance over convenience, explicit over clever — and when in doubt, ask before inventing.
