"""Case-domain persistence queries. Every query is tenant-scoped."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Case,
    CaseWallet,
    Decision,
    EvidenceItem,
    Finding,
    Wallet,
)


async def get_case(session: AsyncSession, tenant_id: UUID, case_id: UUID) -> Case | None:
    result = await session.execute(
        select(Case).where(Case.id == case_id, Case.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_cases(
    session: AsyncSession, tenant_id: UUID, *, limit: int, offset: int
) -> list[Case]:
    result = await session.execute(
        select(Case)
        .where(Case.tenant_id == tenant_id)
        .order_by(Case.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars())


async def get_wallet_by_address(
    session: AsyncSession, tenant_id: UUID, workspace_id: UUID, chain: str, address: str
) -> Wallet | None:
    result = await session.execute(
        select(Wallet).where(
            Wallet.tenant_id == tenant_id,
            Wallet.workspace_id == workspace_id,
            Wallet.chain == chain,
            Wallet.address == address,
        )
    )
    return result.scalar_one_or_none()


async def get_case_wallet_link(
    session: AsyncSession, tenant_id: UUID, case_id: UUID, wallet_id: UUID
) -> CaseWallet | None:
    result = await session.execute(
        select(CaseWallet).where(
            CaseWallet.tenant_id == tenant_id,
            CaseWallet.case_id == case_id,
            CaseWallet.wallet_id == wallet_id,
        )
    )
    return result.scalar_one_or_none()


async def list_case_wallets(
    session: AsyncSession, tenant_id: UUID, case_id: UUID
) -> list[tuple[CaseWallet, Wallet]]:
    result = await session.execute(
        select(CaseWallet, Wallet)
        .join(Wallet, CaseWallet.wallet_id == Wallet.id)
        .where(CaseWallet.tenant_id == tenant_id, CaseWallet.case_id == case_id)
        .order_by(CaseWallet.created_at)
    )
    return [(row.CaseWallet, row.Wallet) for row in result]


async def list_case_evidence(
    session: AsyncSession, tenant_id: UUID, case_id: UUID
) -> list[EvidenceItem]:
    result = await session.execute(
        select(EvidenceItem)
        .where(EvidenceItem.tenant_id == tenant_id, EvidenceItem.case_id == case_id)
        .order_by(EvidenceItem.created_at)
    )
    return list(result.scalars())


async def list_case_findings(
    session: AsyncSession, tenant_id: UUID, case_id: UUID
) -> list[Finding]:
    result = await session.execute(
        select(Finding)
        .where(Finding.tenant_id == tenant_id, Finding.case_id == case_id)
        .order_by(Finding.created_at.desc())
    )
    return list(result.scalars())


async def list_case_decisions(
    session: AsyncSession, tenant_id: UUID, case_id: UUID
) -> list[Decision]:
    result = await session.execute(
        select(Decision)
        .where(Decision.tenant_id == tenant_id, Decision.case_id == case_id)
        .order_by(Decision.created_at.desc())
    )
    return list(result.scalars())
