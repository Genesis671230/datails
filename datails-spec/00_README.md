# Datails — Claude Code Specification Package

This folder is the complete, self-contained input for Claude Code to build the Datails backend. Give Claude Code all eight files (this README plus the seven numbered spec files), in this order. The package is reconciled with the **Foundation — AI Workspace v7.0** set (canonical narrative) as of 9 July 2026.

## Reading order

| # | File | Role |
|---|---|---|
| 01 | `01_PRODUCT_SPEC.md` | What Datails is and what the Phase 1 backend must do |
| 02 | `02_ARCHITECTURE_SPEC.md` | How the system must be structured: blocks, layers, rules |
| 03 | `03_IMPLEMENTATION_PLAN.md` | Exact build order: phases, tables, endpoints, checkpoints |
| 04 | `04_ERRATA_LOCKED_DECISIONS.md` | Binding corrections and locked decisions (LD-1 – LD-30) |
| 05 | `05_DOMAIN_MODEL.md` | Domain knowledge from operator discovery: schema deltas, enums, seeds, guardrails |
| 06 | `06_CLAUDE_CODE_MASTER_PROMPT.md` | Behavior contract for Claude Code during the build |
| 07 | `07_BUILD_PLAN.md` | **Authoritative build sequence**: four slices, prerequisites, acceptance = the demonstrable loop |

## Precedence on conflict

`04_ERRATA_LOCKED_DECISIONS.md` **wins over** files 01–03.
`05_DOMAIN_MODEL.md` refines schema and content within the errata's constraints; where it specifies a table or enum, it wins over the generic versions in 01–03.
`06_CLAUDE_CODE_MASTER_PROMPT.md` governs behavior, not architecture.
`07_BUILD_PLAN.md` governs **sequence and acceptance**; `03_IMPLEMENTATION_PLAN.md` remains the content reference for tables, routes, and rules (LD-26).

If a gap is covered by none of these files: stop and ask; do not invent (see file 06).

## Provenance

Files 01–03 were authored by the founder (content unchanged except clearly marked amendment notes in italics; conversational fragments and external links removed). File 05 is distilled from the Operator Intelligence Knowledge Base (`Transcripts/Operator_Intelligence_KB/`), where every claim carries a citation to a source transcript. Citation IDs like [02-16] refer to that KB's transcript index; they are provenance only — the code generator does not need to resolve them.
