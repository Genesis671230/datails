# Datails — Claude Code Master Prompt

You are building the Datails backend. This file governs **how you behave** while building. The other seven files in this folder (00–05, 07) govern **what** you build and in **what order** (`00_README.md` defines reading order and precedence).

***

## Prime directives

1. **Slice by slice, in order.** Follow `07_BUILD_PLAN.md` for sequence and acceptance (LD-26), with `03_IMPLEMENTATION_PLAN.md` as the content reference for tables, routes, and rules, all as amended by `04_ERRATA_LOCKED_DECISIONS.md`. Never start a slice before the previous slice's acceptance — including its test requirements (LD-10) — is fully green. Never build ahead "while you're in there."
2. **Locked decisions are locked.** LD-1 through LD-30 are not suggestions. If a locked decision proves impossible or contradictory during implementation, STOP, describe the conflict precisely, and ask. Do not substitute your own alternative.
3. **Do not invent architecture.** If something is not covered by the eight spec files, do not fill the gap with a convenience choice. Ask first. Small implementation details (variable names, obvious idioms) are yours; anything touching schema, module boundaries, security, ledgers, or AI behavior is not.
4. **The object model is the product.** When in doubt about where logic lives, follow the block boundaries in `02_ARCHITECTURE_SPEC.md`. Route handlers stay thin. Services own logic. Repositories own persistence. Ledger writes, AI logging, snapshots, and usage records happen in explicit service flows.
5. **Provenance over convenience.** Every connector retrieval follows the LD-4 ingestion sequence. Every decision write emits its ledger event in the same transaction (LD-9). Every AI call is logged (Phase 7/10). No unlogged background behavior.

## Working rhythm

For every unit of work:

1. State which slice you are in and what the unit delivers.
2. Implement in small, reviewable increments — one module or one route surface at a time.
3. For each new module/service/route, explain: what it does, why it belongs in that module, what it depends on, and what data path it affects (per `02_ARCHITECTURE_SPEC.md` explainability rule).
4. Write the tests required by LD-10 alongside the code, not after the slice.
5. Keep commits small and meaningful; commit messages name the slice.
6. Update `IMPLEMENTATION_STATUS.md` at every slice boundary: completed slices, current slice, open blockers, next milestone. At the same boundary, write `docs/build-log/<date>-<slice>.md` (endpoints and tables added, decisions made, test status, how to verify) and append any newly deferred item to `BACKLOG.md` with a reason (LD-26).
7. Keep `README.md`, `ARCHITECTURE.md`, `MODULES.md`, `DECISIONS.md` current as you go. New deliberate choices (and their rationale) go into `DECISIONS.md` at the moment they're made — including the pre-seeded entries required by LD-2 (no workers), LD-3 (hash-chaining deferral), LD-9 (source-of-truth rule), LD-16 (KYC obligation), and `05_DOMAIN_MODEL.md` §4.3 (deferred integrations).

## Naming

In code, schema, routes, and technical docs the agents are **workflow agents** (`workflow_agents`, `/api/v1/workflow-agents`); "Digital Colleagues" / "AI agents" appear only in user-facing copy (LD-21).

## Hard-stop checks (verify before every slice transition)

- App boots; migrations apply and roll back.
- All tests green in CI, including tenant-isolation tests.
- No secrets in code or database; Key Vault references only.
- Ledger tables reject UPDATE/DELETE at the database level.
- Routes are thin; no business logic, connector calls, or model calls in handlers.
- Every AI call path logs to `ai_call_log`; every connector run follows LD-4 (scoped per LD-18: full sequence applies once Blob Storage and the ledgers exist; the Phase 4 test call persists nothing).
- Tenant context derives only from the validated Entra JWT (LD-1) — never from client-supplied values.

If any check fails, fix it before proceeding. Do not defer with a TODO.

## Domain fidelity

`05_DOMAIN_MODEL.md` is distilled from real investigator discovery. When writing seed data, enums, agent role instructions, or prompt templates, use its vocabulary and rules exactly — e.g., the hot-wallet trace boundary, label provenance, the five W's, human gates on freeze letters and SARs. Do not "improve" domain content from general knowledge; it was validated with operators, and citations trace to transcripts.

Two standing guardrails from that evidence:

- **Never implement autonomous tracing logic.** Tracing heuristics are prompt/SOP content for human-led work, not algorithms.
- **Never bypass a human approval gate** on findings promotion, freeze/blocklist letters, SAR drafts, or report finalization.

## Asking vs. deciding

Ask (stop and raise) when: a locked decision conflicts with reality; a dependency is missing (e.g., Crystal spike results, Entra tenant configuration, explorer vendor selection per LD-15); two spec files genuinely contradict and precedence (per `00_README.md`) doesn't resolve it; or a security-relevant choice is unspecified.

Decide silently when: naming, file organization within a prescribed folder, standard library/idiom choices, test structure — anything reversible that touches no boundary.

## Tone of the codebase

Boring, explicit, readable. A senior engineer reviewing this repo cold should understand any module in minutes. Favor five clear lines over one clever one. Docstrings state purpose; comments explain intent, not mechanics.
