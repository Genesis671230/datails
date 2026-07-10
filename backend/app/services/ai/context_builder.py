"""Case context builder (LD-5, 05 §5).

THE single place case context is assembled — no route, agent, or report
service may assemble context independently.

Fixed inclusion priority (truncate from the bottom when over budget):
1. Case core: title, type, status, running summary
2. Approved findings (newest first)
3. Decisions (newest first)
4. Wallets with current labels incl. provenance refs and wallet_kind flags
5. Evidence references (titles/refs only — never raw payloads)
6. Methodology cues relevant to the task type and case_type
7. Unapproved / draft findings

Every assembly emits the source references used, so AI outputs can cite
them. Cache: in-process (Redis deferred, LD-21), 15-minute TTL, keyed
case_id + max(updated_at across the case graph) — any write to the case
graph changes the key and thus invalidates naturally.

Token budget: approximated at 4 characters/token (documented pilot
heuristic; exact tokenizers vary per model and would add a dependency for
marginal gain at this scale).
"""

import time
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import (
    Case,
    Methodology,
    MethodologyStep,
    Wallet,
    WalletLabel,
)
from app.db.repositories.cases import (
    get_case,
    list_case_decisions,
    list_case_evidence,
    list_case_findings,
    list_case_wallets,
)

CHARS_PER_TOKEN = 4
CACHE_TTL_SECONDS = 15 * 60


@dataclass(frozen=True)
class CaseContext:
    case_id: UUID
    text: str
    source_refs: list[str]
    token_estimate: int
    truncated_sections: list[str]


@dataclass
class _CacheEntry:
    key: str
    built_at: float
    context: CaseContext


_cache: dict[UUID, _CacheEntry] = {}


@dataclass
class _Section:
    name: str
    lines: list[str] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)


def _estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


async def _cache_key(session: AsyncSession, case: Case) -> str:
    """case_id + max(updated_at across the case graph), per LD-5.

    Children carry created_at only (append-oriented domain), so the max spans
    case.updated_at and child created_at values — any child write moves it.
    """
    from sqlalchemy import func

    from app.db.models import CaseWallet, Decision, EvidenceItem, Finding, WalletLabel

    timestamps = [case.updated_at]
    for model, column in (
        (Finding, Finding.created_at),
        (Decision, Decision.created_at),
        (EvidenceItem, EvidenceItem.created_at),
        (CaseWallet, CaseWallet.created_at),
    ):
        result = await session.execute(
            select(func.max(column)).where(model.case_id == case.id)
        )
        value = result.scalar_one_or_none()
        if value is not None:
            timestamps.append(value)
    # Labels hang off wallets, not cases; join through the case link.
    label_max = (
        await session.execute(
            select(func.max(WalletLabel.created_at))
            .join(CaseWallet, CaseWallet.wallet_id == WalletLabel.wallet_id)
            .where(CaseWallet.case_id == case.id)
        )
    ).scalar_one_or_none()
    if label_max is not None:
        timestamps.append(label_max)
    return f"{case.id}:{max(timestamps).isoformat()}"


async def _current_labels(
    session: AsyncSession, wallet_ids: list[UUID]
) -> dict[UUID, list[WalletLabel]]:
    """Latest observation per (wallet, label) — labels are append-only (LD-14)."""
    if not wallet_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(WalletLabel)
                .where(WalletLabel.wallet_id.in_(wallet_ids))
                .order_by(WalletLabel.observed_at.desc())
            )
        )
        .scalars()
        .all()
    )
    latest: dict[tuple[UUID, str], WalletLabel] = {}
    for row in rows:
        latest.setdefault((row.wallet_id, row.label), row)
    grouped: dict[UUID, list[WalletLabel]] = {}
    for label in latest.values():
        grouped.setdefault(label.wallet_id, []).append(label)
    return grouped


async def _methodology_cues(
    session: AsyncSession, case: Case, task_type: str
) -> list[str]:
    """Methodology step cues for this tenant, shaped by task type (05 §5)."""
    methodology = (
        await session.execute(
            select(Methodology)
            .where(
                Methodology.tenant_id == case.tenant_id,
                Methodology.is_active.is_(True),
            )
            .order_by(Methodology.created_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    if methodology is None:
        return []
    steps = (
        (
            await session.execute(
                select(MethodologyStep)
                .where(MethodologyStep.methodology_id == methodology.id)
                .order_by(MethodologyStep.step_order)
            )
        )
        .scalars()
        .all()
    )
    if task_type == "report_drafting":
        steps = [s for s in steps if "report" in (s.tool_preference or "").lower()
                 or "report" in (s.output_type or "").lower()]
    cues = [
        f"Step {s.step_order} — {s.step_name}: {s.description or ''}"
        + (" [requires human approval]" if s.requires_human_approval else "")
        for s in steps
    ]
    return cues


def _wallet_line(wallet: Wallet, role, labels: list[WalletLabel]) -> tuple[str, list[str]]:
    parts = [f"{wallet.address} ({wallet.chain}"]
    if wallet.wallet_kind is not None:
        # Hot-wallet boundaries change tracing advice (05 §5).
        parts.append(f", kind={wallet.wallet_kind.value}")
    if role is not None:
        parts.append(f", role={role.value}")
    parts.append(")")
    refs = []
    label_texts = []
    for label in labels:
        provenance = (
            f"data_ledger:{label.data_ledger_id}" if label.data_ledger_id else "user"
        )
        label_texts.append(f"{label.label} [{provenance}]")
        if label.data_ledger_id:
            refs.append(f"data_ledger:{label.data_ledger_id}")
    line = "".join(parts)
    if label_texts:
        line += " labels: " + "; ".join(label_texts)
    return line, refs


async def build_case_context(
    session: AsyncSession, tenant_id: UUID, case_id: UUID, task_type: str
) -> CaseContext:
    """Assemble (or serve from cache) the scoped context for one case."""
    from app.services.ai.model_router import get_route

    case = await get_case(session, tenant_id, case_id)
    if case is None:
        raise NotFoundError("Case not found.")

    key = await _cache_key(session, case)
    cached = _cache.get(case_id)
    if cached and cached.key == key and time.monotonic() - cached.built_at < CACHE_TTL_SECONDS:
        return cached.context

    budget_tokens = get_route(task_type).context_budget_tokens

    findings = await list_case_findings(session, tenant_id, case_id)
    approved = [f for f in findings if f.approved_at is not None]
    drafts = [f for f in findings if f.approved_at is None]
    decisions = await list_case_decisions(session, tenant_id, case_id)
    wallet_pairs = await list_case_wallets(session, tenant_id, case_id)
    labels_by_wallet = await _current_labels(
        session, [wallet.id for _, wallet in wallet_pairs]
    )
    evidence = await list_case_evidence(session, tenant_id, case_id)
    cues = await _methodology_cues(session, case, task_type)

    # Sections in LD-5 priority order.
    sections: list[_Section] = []

    core = _Section("case_core")
    core.lines = [
        f"Case: {case.title}",
        f"Type: {case.case_type.value} | Status: {case.status.value} "
        f"| Priority: {case.priority.value}",
    ]
    if case.summary:
        core.lines.append(f"Running summary: {case.summary}")
    core.refs = [f"case:{case.id}"]
    sections.append(core)

    approved_section = _Section("approved_findings")
    for finding in approved:
        approved_section.lines.append(
            f"[APPROVED] {finding.title}: {finding.content or ''}"
        )
        approved_section.refs.append(f"finding:{finding.id}")
        if finding.source_ref:
            approved_section.refs.append(finding.source_ref)
    sections.append(approved_section)

    decisions_section = _Section("decisions")
    for decision in decisions:
        decisions_section.lines.append(
            f"[DECISION {decision.decision_type.value}] {decision.description}"
            + (f" — rationale: {decision.rationale}" if decision.rationale else "")
        )
        decisions_section.refs.append(f"decision:{decision.id}")
    sections.append(decisions_section)

    wallets_section = _Section("wallets")
    for link, wallet in wallet_pairs:
        line, refs = _wallet_line(wallet, link.role_in_case, labels_by_wallet.get(wallet.id, []))
        wallets_section.lines.append(line)
        wallets_section.refs.extend(refs)
        wallets_section.refs.append(f"wallet:{wallet.id}")
    sections.append(wallets_section)

    evidence_section = _Section("evidence_refs")
    for item in evidence:
        # References and titles only — never full raw payloads (LD-5).
        evidence_section.lines.append(
            f"Evidence [{item.evidence_type.value}]: {item.title}"
        )
        evidence_section.refs.append(f"evidence:{item.id}")
    sections.append(evidence_section)

    cues_section = _Section("methodology_cues", lines=cues)
    sections.append(cues_section)

    drafts_section = _Section("draft_findings")
    for finding in drafts:
        drafts_section.lines.append(f"[DRAFT] {finding.title}: {finding.content or ''}")
        drafts_section.refs.append(f"finding:{finding.id}")
    sections.append(drafts_section)

    # Truncate from the bottom (LD-5): drop whole sections, lowest priority first.
    truncated: list[str] = []
    included = list(sections)
    while included:
        text = "\n\n".join(
            f"## {s.name}\n" + "\n".join(s.lines) for s in included if s.lines
        )
        if _estimate_tokens(text) <= budget_tokens or len(included) == 1:
            break
        dropped = included.pop()
        if dropped.lines:
            truncated.append(dropped.name)

    text = "\n\n".join(f"## {s.name}\n" + "\n".join(s.lines) for s in included if s.lines)
    source_refs: list[str] = []
    for section in included:
        for ref in section.refs:
            if ref not in source_refs:
                source_refs.append(ref)

    context = CaseContext(
        case_id=case_id,
        text=text,
        source_refs=source_refs,
        token_estimate=_estimate_tokens(text),
        truncated_sections=truncated,
    )
    _cache[case_id] = _CacheEntry(key=key, built_at=time.monotonic(), context=context)
    return context


def clear_context_cache() -> None:
    """Test hook."""
    _cache.clear()
