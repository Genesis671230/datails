# Kickoff prompt for Claude Code

Copy everything inside the code block below and paste it as your first message to Claude Code, opened in this repository.

```
You are building the Datails backend from a complete specification package.

READ FIRST, in this exact order, before writing any code:
1. datails-spec/00_README.md        — reading order and precedence rules
2. datails-spec/01_PRODUCT_SPEC.md  — what Datails is
3. datails-spec/02_ARCHITECTURE_SPEC.md — blocks, layers, coding rules
4. datails-spec/03_IMPLEMENTATION_PLAN.md — tables, routes, rules (content reference)
5. datails-spec/04_ERRATA_LOCKED_DECISIONS.md — LD-1 to LD-30, binding, wins on conflict
6. datails-spec/05_DOMAIN_MODEL.md  — canonical schema deltas, enums, seeds, guardrails
7. datails-spec/06_CLAUDE_CODE_MASTER_PROMPT.md — your behavior contract; follow it fully
8. datails-spec/07_BUILD_PLAN.md    — authoritative build order: four slices

Then:
- Confirm in one short summary: the slice plan, the precedence rules, and the
  LD decisions that constrain Slice 0. Flag anything you find contradictory
  or unbuildable BEFORE starting. Do not paraphrase the whole spec.
- Day-one prerequisite status: none ready yet — build and test everything
  locally with Docker (Postgres via docker-compose, mocked Key Vault and Blob,
  recorded Crystal fixtures, AUTH_DEV_MODE for local only per LD-1). I will
  provide the Azure resource group, Foundry deployments, Entra app
  registration, Crystal key, and the anonymised AQ case dataset later.
  Ask me for each one at the moment a slice actually needs it, and use a
  placeholder fixture for the AQ case until the real dataset arrives.
- Then begin SLICE 0 exactly as defined in 07_BUILD_PLAN.md.

Standing rules (details in 06, they win over habit):
- Slice by slice; never build ahead. Acceptance + tests green before the next slice.
- LD-1 to LD-30 are locked. If one proves impossible, stop and ask — never
  substitute your own alternative.
- Anything not covered by the eight spec files: ask before inventing.
- Every slice boundary: update IMPLEMENTATION_STATUS.md, write
  docs/build-log/<date>-<slice>.md, append deferrals to BACKLOG.md.
- Terminology in code: workflow_agents, never digital_colleagues.
- No secrets in code. No autonomous tracing. No bypassed human gates.

Work in small, reviewable commits named by slice. Start now.
```

## Continuing after a long session

Start a fresh Claude Code session with the same prompt, plus this line at the end:

```
This is a continuation. Read IMPLEMENTATION_STATUS.md and docs/build-log/ first,
then continue from where the last session stopped.
```
