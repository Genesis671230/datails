# Datails — Build Plan (v0: four slices)

**This file is the authoritative build order** (LD-26). `03_IMPLEMENTATION_PLAN.md` remains the authoritative content reference for table columns, route contracts, and rules — this file dictates *sequence and acceptance*. Founder + Claude Code build; target: first live version within days.

**Overall acceptance = the demonstrable loop** (Foundation, Pilot Scope): open a case → connect data via the Crystal connector → Workflow Agent traces fund flow hop-by-hop under FIFO with per-step confirmation → case memory persists across sessions → transaction-explorer graph → cited, court-ready report draft → every step in the ledgers. **Real anonymised AQ Forensics case. Bitcoin first.**

***

## Day-one prerequisites (founder, before or parallel to Slice 0)

- [ ] Azure subscription; resource group in **West Europe** (LD-23)
- [ ] Azure AI Foundry access; **GPT-4o + GPT-4o-mini deployments in West Europe verified, incl. quota** (LD-24)
- [ ] Entra External ID app registration (SPA + API; note tenant ID, client IDs, authority URL) (LD-1)
- [ ] Crystal temporary API key received → straight into Key Vault (LD-22)
- [ ] Empty GitHub repository; GitHub Actions OIDC federation to Azure
- [ ] **Anonymised AQ case dataset**: wallets, tx hashes, expected hops — the seed fixture and demo script
- [ ] Cohort Data & Methodology Permission signature status per member (gates `learning_capture_enabled`, LD-30)

Slices 0–2 build and run locally against Docker if Azure prerequisites lag; only deployment blocks.

***

## Slice 0 — Foundation (target: day 1)

Everything after this slice is feature work.

**Build:**

- Repo scaffold per the canonical tree (LD-2); FastAPI, Docker, docker-compose with Postgres; config loader; structured logging; error middleware; `/api/v1/health`.
- **One migration, full core schema:** tenants (incl. `learning_capture_enabled`, `credit_limit_usd`, `region`), users, workspaces, onboarding_sessions, methodologies + methodology_steps + generated_templates (+ `jurisdiction_variants_json`, LD-19), workflow_agent_profiles, cases, wallets + case_wallets + wallet_labels (LD-13/14), evidence_items, findings, decisions, connectors (incl. `credential_owner`) + connector_runs, traces + trace_hops (§8), data_ledger + decision_ledger + ai_call_log + learning_events (insert-only grants + triggers, LD-3), idempotency_keys, usage_records, tenant_plan_state, workflow_agents + workflow_agent_runs. All enums from `05_DOMAIN_MODEL.md` §1.3/1.3a as DB enums.
- Entra JWT validation middleware (LD-1) + `POST /api/v1/workspaces/bootstrap` + `GET /api/v1/workspaces/me`.
- Methodology seed data (AQ baseline, `05_DOMAIN_MODEL.md` §2) + anonymised AQ case fixture + **recorded Crystal response fixtures** (mock/replay mode for dev and CI).
- OpenAPI spec published (LD-26). Bicep skeleton with region parameter; PITR + Blob soft-delete in templates (LD-29).

**Accept:** app boots; migration up/down clean; ledger tables reject UPDATE/DELETE; valid Entra JWT → tenant context, missing/invalid → 401; tenant-isolation test passes; fixtures load; CI green.

***

## Slice 1 — Case + Crystal ingestion (target: day 2)

**First live moment: wallet in → enriched case.**

**Build:**

- Case domain routes (03 Phase 5 list) with `GET /api/v1/cases/{id}` returning findings + decisions (LD-8); decision writes emit ledger events same-transaction (LD-9; backfill n/a — ledgers exist from Slice 0, so LD-18.1 collapses: the rule applies from the first decision).
- Connector interface + Crystal connector #1 behind it: `risk_check` and `full_investigation` modes (LD-22); Key Vault secret resolution; LD-4 ingestion sequence (blob → hash → data_ledger same-transaction); wallet-lookup + attach-to-case routes; label writes into `wallet_labels` with `data_ledger_id` provenance (LD-14).
- Shared-key global budget + per-connector `daily_call_limit` (derived from connector_runs, LD-11) enforcement.
- Idempotency middleware on expensive POSTs (LD-28).

**Accept:** real Crystal call (temp key) round-trips: snapshot in Blob (or local emulator), hash in data_ledger, labels with provenance on the wallet, visible via `GET /api/v1/ledger/data`; replay of the same Idempotency-Key returns the original response; CI runs entirely on recorded fixtures.

***

## Slice 2 — AI layer (target: day 3)

**Build:**

- Context builder (LD-5: 8k budget, inclusion priority, 15-min cache, source refs out) — in-process cache (Redis deferred, LD-21).
- Foundry client wrapper + `model_router.py` (GPT-4o reasoning / 4o-mini formatting, LD-24); every call → `ai_call_log`.
- `POST /api/v1/ai/assistant` (LD-20).
- Report generation: `POST /api/v1/reports/draft` + versions + approve (03 Phase 12); report types incl. `freeze_blocklist_request`, `sar_draft` (LD-17); drafts cite data_ledger/evidence refs; jurisdiction variant applied at draft time.
- **Learning-event capture** wired into draft approve/reject, report edits, assistant accept/reject — gated by `learning_capture_enabled` (LD-30).
- Golden-set smoke test (3–5 fixture cases → draft properties asserted) (LD-29).

**Accept:** assistant returns a case-grounded, source-cited answer on the AQ fixture; report draft cites sources; approval creates version + ledger event; ai_call_log rows complete (model, tokens, hashes); learning_events appear only when the tenant flag is true; golden set green.

***

## Slice 3 — Trace loop + deploy (target: day 4–5)

**Build:**

- FIFO engine (deterministic, engine-side) + Workflow Agent run loop: propose hop → present amounts/labels/confidence/boundary flags → investigator confirm/reject → next hop. State machine + resumability (LD-27). Trace routes (§8). Hop confirmations → decision_ledger same-transaction. Hot-wallet boundary ends traversal and proposes an exchange information request.
- Transaction-explorer graph output (nodes = wallets with labels+provenance; edges = confirmed hops with confidence).
- **Case memory acceptance test (named):** close session → reopen case → full context (wallets, hops, findings, drafts) present without re-entry.
- Deploy: Bicep (Container Apps, Postgres Flexible Server + PITR, Key Vault, Blob + soft-delete, Foundry, Application Insights; region=westeurope) + GitHub Actions OIDC pipeline; budget alert; `docs/RUNBOOK.md` (ACA revision rollback, Crystal key rotation, demo-failure checklist) (LD-25/29).

**Accept:** the full demonstrable loop runs in Azure on the anonymised AQ case, Bitcoin, end-to-end, with every step inspectable in the ledgers; interrupt-and-resume of a trace run works; rollback procedure tested once.

***

## Explicitly deferred (append to BACKLOG.md at Slice 0, per LD-26)

Risk-rule engine · entity registry lite · CrimeTrace ingestion endpoint · credit backstop (402) behavior · usage metering (record writes + `GET /api/v1/usage/summary`; the `usage_records`/`tenant_plan_state` tables exist from Slice 0) · methodology CRUD routes (seed data only in pilot) · UAE North stamp · MCP connectors · BYO keys UX · Redis cache · multi-chain beyond BTC · workflow-template library · Learning-Layer analytics · frontend build (separate track: Lovable UX export → GitHub → Claude Code builds against the OpenAPI contract; Entra PKCE tested with a real token first).

***

## Working rhythm reminders (from `06_CLAUDE_CODE_MASTER_PROMPT.md`)

Per slice: build-log entry in `docs/build-log/` + BACKLOG.md updates + IMPLEMENTATION_STATUS.md + tests per LD-10 green before the next slice. Hard-stop checks apply at every slice boundary.
