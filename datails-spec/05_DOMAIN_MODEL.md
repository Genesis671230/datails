# Datails — Domain Model

Domain knowledge distilled from operator discovery (Nov 2025 – May 2026: Albert Quimberger / AQ Forensics, Crystal Intelligence first-party, builder input). Citation IDs like [02-16] refer to the transcript index in `Transcripts/Operator_Intelligence_KB/15_transcript_index/`. Full mechanics: KB section 17.

This file refines schema and content within the constraints of `04_ERRATA_LOCKED_DECISIONS.md`. Where it defines a table or enum, it supersedes the generic version in `03_IMPLEMENTATION_PLAN.md`.

***

## 1. Schema deltas (Phase 5)

### 1.1 Wallets are workspace-global (LD-13)

Criminal organizations reuse wallet infrastructure across cases; a wallet seen in case A must surface in case B [02-16]. Replace the case-scoped `case_wallets` design with:

#### wallets

- id (uuid, pk)
- tenant_id (fk)
- workspace_id (fk)
- address
- chain
- wallet_kind (nullable: hot_wallet | self_hosted | cold_storage | smart_contract | unknown)
- is_watched (boolean, default false) — schema hook for dormant-wallet monitoring [02-16]; no monitoring behavior in Phase 1
- first_seen_at
- created_at

Unique constraint: (workspace_id, chain, address).

#### case_wallets (join)

- id (uuid, pk)
- case_id (fk)
- wallet_id (fk)
- tenant_id (fk)
- role_in_case (nullable: victim | suspect | intermediary | exchange_deposit | unknown)
- added_by (fk users)
- created_at

### 1.2 Wallet labels carry provenance (LD-14)

"Binance, per Crystal, on date X" is evidence; a bare string is not. Labeling is the core value of intelligence vendors [02-16] and must be traceable to its retrieval.

#### wallet_labels

- id (uuid, pk)
- wallet_id (fk)
- tenant_id (fk)
- label (e.g., entity name: "Binance", "Tornado Cash")
- label_type (entity | risk_flag | scam_reference | user_note)
- risk_color (nullable: green | yellow | red) — regulated / unregulated / sanctioned convention [02-16]
- source_type (connector | user | import)
- connector_id (nullable fk)
- data_ledger_id (nullable fk) — provenance link, REQUIRED when source_type = connector
- observed_at
- created_at

Labels are never overwritten: a newer observation is a new row. "Current label" = latest by observed_at.

### 1.3 Enum values (evidence-backed)

**case_type** [02-16 §three pillars; six verticals all starting from "a transaction or a wallet ID"]:
`criminal_investigation | proof_of_source_of_funds | digital_inheritance | divorce | bankruptcy | tax_reconstruction`
Phase 1 workflows only need `criminal_investigation`; the enum ships complete because the spine is shared.

**evidence_type** must include:
`transaction_history_export` (the single best victim evidence artifact [02-16]) | `screenshot` | `communication_record` | `exchange_correspondence` | `police_file_reference` (Akteneinsicht/Onlinewache [02-16]) | `on_chain_snapshot` | `other`

**decision_type** must include:
`open_case | freeze_request_sent | report_filed | sar_filed | case_closed | escalation | other`

**Scam typology** (metadata vocabulary for cases, not a table) [02-16]:
investment_scam, recovery_scam, romance_scam, smishing, social_engineering, hack, pickpocketing.

### 1.3a Status and operational enums (pilot defaults)

These are **not** domain-evidenced; they are pilot defaults so the code generator never has to invent values. Changing them requires only a `DECISIONS.md` entry, not an erratum.

- `cases.status`: `open | active | on_hold | closed`
- `cases.priority`: `low | medium | high | urgent`
- `finding_type`: `wallet_attribution | transaction_trace | entity_identification | evidence_summary | risk_assessment | other`
- `connectors.status`: `active | disabled | error`
- `connector_runs.status`: `pending | running | completed | failed`
- `workflow_agent_runs.status`: per LD-27 — `pending | running | awaiting_confirmation | completed | failed | abandoned`
- `reports.status`: `draft | in_review | approved | final`
- `onboarding_sessions.status`: `started | completed | abandoned`
- `decision_ledger.event_type`: `created | approved | rejected | superseded | revoked`
- `usage_records.category`: `ai_task | connector_run | report_generation | storage`

### 1.4 Report types (Phase 12, LD-17)

`report_type` enum:
`police_intake | exchange_compliance_request | freeze_blocklist_request | investigator_summary | case_dossier | sar_draft`

- **freeze_blocklist_request** is first-class: per-platform, per-jurisdiction letter with tx hashes, always behind a human approval gate. Named targets from the corpus: Binance, KuCoin, MEXC (CEX freeze); ChangeNOW, FixedFloat, 1inch, Uniswap (DeFi blocklisting via smart-contract sanctions lists) [02-16], [02-19].
- **sar_draft**: SAR/STR to an FIU requires department-head approval inside the customer's institution [02-16] — the draft is generated, the approval is theirs.

### 1.5 Jurisdiction dimension (Phase 3 + 12)

Jurisdiction affects report *wording*, mostly small deltas (EU→UK difference ≈ two sentences on the front page [02-16]). Model as: base template + jurisdiction variant overlays, not separate templates.

Jurisdiction vocabulary (initial): `EU (MiCA, Travel Rule, DAC8, CARF) | UK | US (OFAC, subpoena route) | AT | DE | CH | AE`. Store per methodology (`jurisdictions_json`) and per report (chosen at draft time).

***

## 2. Methodology seed data (Phase 3)

Ship Phase 3 with a pre-built **baseline investigation methodology** derived from AQ Forensics practice, as seed data — the pilot must feel like "it already knows how I work," not an empty engine. Seed steps (maps 1:1 onto `methodology_steps`):

| # | step_name | description (source) | tool_preference | output_type | requires_human_approval |
|---|---|---|---|---|---|
| 1 | Victim intake (five W's) | Who lost what/how much to whom/which wallet; reconstruct on-ramp; identify fiat→crypto mixing point [02-16], [12-12] | intake form / conversation | structured intake record | no |
| 2 | Evidence collection | Transaction-history export from on-ramp exchange; screenshots; communications [02-16] | file upload | evidence_items | no |
| 3 | Parallel police filing | Guide victim to official filing (Onlinewache model); record file reference [02-16] | — | police_file_reference | no |
| 4 | Preliminary wallet check | Validate addresses; quick lookup on submitted wallets [02-16] | connector | preliminary trace summary | no |
| 5 | On-chain tracing | Investigator-led exploration: labels, change outputs, hot-wallet boundaries, chain hops [02-16] | Crystal connector | findings | yes (findings approval) |
| 6 | Freeze / blocklist communication | Per-platform letters with hashes to CEX/DeFi [02-16], [02-19] | report generator | freeze_blocklist_request | **yes** |
| 7 | Regulatory reporting | SAR/STR draft to FIU; jurisdiction wording [02-16] | report generator | sar_draft | **yes** |
| 8 | Court-ready report | Source-hyperlinked, jurisdiction-specific final report [02-16] | report generator | police_intake / case_dossier | **yes** |

Albert's compression of the same pipeline — *"input/aggregation, analysis/making it readable, report/communication"* [02-16] — is the three-pillar structure the UI should mirror.

***

## 3. Agent guardrail content (Phases 9–11)

Tracing heuristics are **encoded knowledge for human-led work — never autonomous algorithms** (spec guardrail + automation fails past mixers [05-21], [12-12]). They belong in colleague `role_instructions`, context-builder content, and report prompts:

**Research Analyst rules** [02-16]:
- Never follow funds *out* of a hot wallet; the trace boundary is the last transaction hash *into* it — the next step is an information request to the exchange, not further graph traversal.
- Change outputs ≠ laundering: change-transaction behavior resembles both peel chains (laundering) and HD wallets (Ledger-style security). Flag the ambiguity; never assert one without metadata.
- Chain-hopping (BTC→ETH→USDC-on-Base→Avalanche) through regulated venues keeps risk scores green; treat "clean" risk scores across multi-chain hops as a caution, not a clearance.
- Some DeFi swaps settle on internal ledgers, not on-chain — mark such segments as blind spots explicitly rather than guessing continuity.
- Always cite label provenance (wallet_labels → data_ledger) in any output that names an entity.

**Intake Analyst rules** [02-16], [12-12]:
- Drive the five W's; require wallet-address validation before intake completes; request the transaction-history export as primary evidence; strip noise (victims deliver ~90% irrelevant material).

**Report Writer rules** [02-16], [02-19]:
- Every claim hyperlinks a source (data_ledger ref or evidence item). Jurisdiction variant applied at draft time. Audience-templated: LEA / exchange / internal versions [02-19]. Drafts only; finalization is human.

**Compliance Analyst rules** [02-16]:
- SAR/STR drafts always route to human approval (mirrors real department-head approval). Exchange communication uses known formats; note that exchanges act on LE requests — private-investigator letters are notifications that prepare the LE handoff, not orders.

***

## 4. Connector layer corrections (Phases 4/8)

### 4.1 Crystal (LD-16)

There is no "Tier 1 / Tier 2" API. Observed surface (Crystal first-party, [03-12]):

- Data APIs: "every bit of information you see in Crystal related to transaction, transfer or entity is retrievable through API."
- **Risk Check API**: fast DB call for risk parameters; heavier deep calls exist separately — design the connector around this two-latency pattern.
- Standard partner starter set: **3–4 cross-compatibility endpoints**.
- **No visualization API** (Graphene internal-only) — Datails builds its own node-based visualization on API data [03-12], [04-15p].
- No direct database access. Monitoring APIs irrelevant (KYT-only).
- **KYC of Datails end customers is mandatory** (Crystal condition) — administrative obligation at tenant onboarding in the pilot (LD-16).
- Unknown until spike (LD-6): rate limits, quotas, pricing, exact endpoint list, payload shapes, pagination, auth mechanics.

`connector_type` values: `crystal | blockchain_explorer | file_upload` (registrable in Phase 1); `generic_api` exists as the base-class/mock type only (LD-19).

### 4.2 Blockchain-explorer connector (LD-15)

The "generic BYO API connector" is instantiated as an Etherscan-class public blockchain-explorer connector: publicly documented API, customer-supplied key, generous free tier. Primary Phase 1 job: **wallet-address validation at intake** and base transaction data. **Caveat: no specific vendor docs are in hand; vendor selection and verification are part of the LD-6 spike scope** — do not hard-code any vendor's payload shapes before the spike.

### 4.3 Future integration candidates (evidence-backed order, NOT Phase 1)

Codex portal (LE↔exchange comms standard) → USSS deconflict (KYC'd investigator lookup) → CoinTracking/Blockpit (tax vertical) [02-16]. Record in DECISIONS.md as deferred; do not build.

***

## 5. Context builder content additions (Phase 9, within LD-5)

The LD-5 inclusion list is extended with: current wallet labels **with provenance refs**, wallet_kind flags (hot-wallet boundaries change tracing advice), and case_type-specific methodology cues (a proof-of-source-of-funds case pulls different cues than a criminal case). Raw payloads still never inline — references only.

***

## 6. Domain vocabulary (for code, prompts, and docs)

| Term | Meaning (source) |
|---|---|
| Five W's | Intake formula: who lost what/how much to whom/which wallet [02-16] |
| Fiat→crypto mixing point | The on-ramp account where fiat became crypto; evidence anchor #1 [02-16] |
| Change output / UTXO | Every BTC spend creates payment + change; metadata needed to read it [02-16] |
| Peel chain | Laundering pattern resembling change behavior [02-16] |
| Hot wallet | Exchange-pooled wallet; ownership changes at deposit; "legal mixing service" [02-16] |
| Chain hopping | Multi-chain laundering through regulated venues keeping risk scores green [02-16] |
| Dusting attack | Tiny sends to expose wallet balance/patterns [02-16] |
| Dormant-wallet monitoring | Alerts on movement of old stolen funds [02-16] |
| 72-hour window | Practical recovery window after a scam [02-16] |
| Freeze / blocklist request | CEX account freeze; DeFi smart-contract sanctions listing [02-16] |
| SAR/STR | Suspicious activity/transaction report to an FIU; dept-head approval [02-16] |
| Deconflict | USSS platform showing which agency investigates a wallet [02-16] |
| Onlinewache | German online police filing; template for accepted official intake [02-16] |

***

## 7. (Reserved — section removed in reconciliation; numbering preserved for cross-references)

***

## 8. Fund-flow trace model (v3 — the pilot's demonstrable loop)

The FIFO trace loop is the pilot acceptance test: wallet in → Crystal enrichment → Workflow Agent proposes hops under FIFO attribution → investigator confirms per hop → transaction-explorer graph → cited report. Attribution is deterministic engine work; the model only reasons/formats (Foundation v7 §5).

#### traces

- id (uuid, pk)
- tenant_id (fk) / workspace_id (fk) / case_id (fk)
- root_wallet_id (fk wallets) — where the stolen funds start
- attribution_method (default `fifo`; future: `lifo | pro_rata` — configuration, not rebuild)
- status (per LD-27: pending | running | awaiting_confirmation | completed | failed | abandoned)
- workflow_agent_run_id (nullable fk)
- created_by (fk users)
- created_at / updated_at

#### trace_hops

- id (uuid, pk)
- trace_id (fk) / tenant_id (fk)
- hop_index (int, 0-based)
- from_wallet_id (fk wallets) / to_wallet_id (fk wallets)
- tx_hash
- asset / chain / amount (numeric)
- confidence (numeric 0–1) — per-hop, surfaced to the investigator
- evidence_refs_json — data_ledger references grounding this hop (labels, Crystal payloads)
- boundary_flag (nullable: hot_wallet | mixer | chain_hop | internal_ledger) — the human-judgment boundaries from [02-16]
- status (proposed | confirmed | rejected)
- confirmed_by (nullable fk users) / confirmed_at
- notes
- created_at

Rules: a hop confirmation writes a `decision_ledger` event in the same transaction (LD-9 pattern); the agent never proposes past an unconfirmed hop; hot-wallet boundaries end graph traversal and propose an exchange information request instead (§3 Research Analyst rules); the final report states the attribution method used.

Routes (added to the canonical endpoint list):

```text
POST /api/v1/cases/{id}/traces
GET  /api/v1/traces/{id}
POST /api/v1/traces/{id}/hops/{hop_id}/confirm
POST /api/v1/traces/{id}/hops/{hop_id}/reject
```

***

## 9. Learning Layer events (v3, per LD-30)

#### learning_events (append-only, insert-only enforced per LD-3)

- id (bigserial pk)
- tenant_id (fk) / workspace_id (fk) / case_id (nullable fk)
- actor_id (nullable fk users)
- event_type: `recommendation_accepted | recommendation_rejected | report_edited | draft_approved | draft_rejected | override | workflow_completed | workflow_abandoned | connector_used | trace_hop_confirmed | trace_hop_rejected | session_duration`
- subject_type / subject_id (what the event is about: report, trace, hop, run…)
- payload_json (deltas, durations, edit sizes — no raw case content duplication)
- created_at

Capture is **gated by `tenants.learning_capture_enabled`** (default false; set true on signed Data & Methodology Permission). Capture only — analytics are post-pilot.

***

## 10. Connector credential model (v3, per LD-22)

- `connectors.credential_owner`: `datails_shared | tenant`. Pilot Crystal = `datails_shared` (temporary key, Key Vault).
- Shared-key global daily budget enforced in the connector execution service, in addition to per-connector `daily_call_limit`.
- Crystal connector modes: `risk_check` ("Tier 1", fast) | `full_investigation` ("Tier 2", deep). Datails product terms; no claim about Crystal's API tiering.
- `connector_type` gains reserved value `mcp_server` (future BYO; not built in the pilot).

***

## 11. Idempotency (v3, per LD-28)

#### idempotency_keys

- key / tenant_id / route / request_hash / response_ref / created_at
- unique (tenant_id, key). Replay → original response; same key + different payload → 409.

Required on: connector runs, workflow-agent runs, trace creation, report drafts, assistant calls.

***

## 12. Tenant additions (v3)

- `tenants.learning_capture_enabled` (bool, default false) — LD-30.
- `tenants.credit_limit_usd` (nullable numeric) — v7 invisible fair-use backstop. **Schema hook only in the pilot**; the HTTP 402 gate behavior is a BACKLOG item.
- `tenants.region` (default `westeurope`) — stamp assignment, LD-23.

***

## 13. What this file deliberately does NOT do

- No autonomous tracing logic (spec guardrail; evidence: automation fails past mixers [05-21]). The FIFO engine (§8) is deterministic arithmetic under per-hop human confirmation — that is the permitted form.
- No victim-facing intake portal (CrimeTrace is a separate build; this backend only exposes the case/evidence APIs it would feed).
- No attribution/labeling engine (vendor IP; partner strategy [02-16], [02-19], [03-12]).
- No monitoring/alerting behavior (only the `is_watched` schema hook).
- No marketplace, no exchange-facing features (insufficient primary evidence).
