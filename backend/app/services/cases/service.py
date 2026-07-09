"""Case domain service: create, list, detail, update, wallet attach, evidence.

Wallets are workspace-global (LD-13): attaching an address to a case first
upserts the wallet in the workspace, then links it through case_wallets — a
wallet observed in one case surfaces automatically in another.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import get_logger, log_fields
from app.db.models import Case, CaseWallet, Decision, EvidenceItem, Finding, Wallet
from app.db.repositories.cases import (
    get_case,
    get_case_wallet_link,
    get_wallet_by_address,
    list_case_decisions,
    list_case_evidence,
    list_case_findings,
    list_case_wallets,
    list_cases,
)
from app.db.repositories.tenancy import get_default_workspace
from app.schemas.cases import CaseCreate, CaseUpdate, EvidenceCreate, WalletAttachRequest

logger = get_logger(__name__)


@dataclass(frozen=True)
class CaseDetail:
    case: Case
    wallets: list[tuple[CaseWallet, Wallet]]
    evidence: list[EvidenceItem]
    findings: list[Finding]
    decisions: list[Decision]


async def _require_case(session: AsyncSession, tenant_id: UUID, case_id: UUID) -> Case:
    case = await get_case(session, tenant_id, case_id)
    if case is None:
        raise NotFoundError("Case not found.")
    return case


async def _require_workspace_id(session: AsyncSession, tenant_id: UUID) -> UUID:
    workspace = await get_default_workspace(session, tenant_id)
    if workspace is None:
        raise NotFoundError("Tenant has no default workspace.")
    return workspace.id


async def create_case(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, data: CaseCreate
) -> Case:
    workspace_id = await _require_workspace_id(session, tenant_id)
    case = Case(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        created_by=user_id,
        title=data.title,
        case_type=data.case_type,
        priority=data.priority,
        summary=data.summary,
        metadata_json=data.metadata,
    )
    session.add(case)
    await session.commit()
    logger.info(
        "case created",
        extra=log_fields(module="cases", action="create", status="ok", case_id=str(case.id)),
    )
    return case


async def list_tenant_cases(
    session: AsyncSession, tenant_id: UUID, *, limit: int, offset: int
) -> list[Case]:
    return await list_cases(session, tenant_id, limit=limit, offset=offset)


async def get_case_detail(session: AsyncSession, tenant_id: UUID, case_id: UUID) -> CaseDetail:
    case = await _require_case(session, tenant_id, case_id)
    return CaseDetail(
        case=case,
        wallets=await list_case_wallets(session, tenant_id, case_id),
        evidence=await list_case_evidence(session, tenant_id, case_id),
        findings=await list_case_findings(session, tenant_id, case_id),
        decisions=await list_case_decisions(session, tenant_id, case_id),
    )


async def update_case(
    session: AsyncSession, tenant_id: UUID, case_id: UUID, data: CaseUpdate
) -> Case:
    case = await _require_case(session, tenant_id, case_id)
    changes = data.model_dump(exclude_unset=True)
    if "metadata" in changes:
        case.metadata_json = changes.pop("metadata")
    for field, value in changes.items():
        setattr(case, field, value)
    await session.commit()
    # updated_at is server-generated on UPDATE; load the fresh value.
    await session.refresh(case)
    logger.info(
        "case updated",
        extra=log_fields(module="cases", action="update", status="ok", case_id=str(case_id)),
    )
    return case


async def attach_wallet(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    case_id: UUID,
    data: WalletAttachRequest,
) -> tuple[CaseWallet, Wallet]:
    """Upsert the workspace-global wallet (LD-13), then link it to the case.

    Re-attaching an already-linked wallet returns the existing link unchanged.
    """
    case = await _require_case(session, tenant_id, case_id)

    wallet = await get_wallet_by_address(
        session, tenant_id, case.workspace_id, data.chain, data.address
    )
    if wallet is None:
        wallet = Wallet(
            tenant_id=tenant_id,
            workspace_id=case.workspace_id,
            address=data.address,
            chain=data.chain,
            wallet_kind=data.wallet_kind,
            first_seen_at=datetime.now(UTC),
        )
        session.add(wallet)
        await session.flush()
    elif data.wallet_kind is not None and wallet.wallet_kind is None:
        wallet.wallet_kind = data.wallet_kind

    link = await get_case_wallet_link(session, tenant_id, case_id, wallet.id)
    if link is None:
        link = CaseWallet(
            case_id=case_id,
            wallet_id=wallet.id,
            tenant_id=tenant_id,
            role_in_case=data.role_in_case,
            added_by=user_id,
        )
        session.add(link)
    await session.commit()
    return link, wallet


async def add_evidence(
    session: AsyncSession, tenant_id: UUID, case_id: UUID, data: EvidenceCreate
) -> EvidenceItem:
    await _require_case(session, tenant_id, case_id)
    evidence = EvidenceItem(
        case_id=case_id,
        tenant_id=tenant_id,
        evidence_type=data.evidence_type,
        title=data.title,
        storage_ref=data.storage_ref,
        source_ref=data.source_ref,
        metadata_json=data.metadata,
    )
    session.add(evidence)
    await session.commit()
    return evidence
