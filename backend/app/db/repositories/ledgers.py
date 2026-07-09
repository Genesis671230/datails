"""Ledger read queries (LD-8): tenant-scoped, newest first."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataLedgerEntry, DecisionLedgerEvent


async def list_data_ledger(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    case_id: UUID | None,
    connector_id: UUID | None,
    limit: int,
    offset: int,
) -> list[DataLedgerEntry]:
    query = select(DataLedgerEntry).where(DataLedgerEntry.tenant_id == tenant_id)
    if case_id is not None:
        query = query.where(DataLedgerEntry.case_id == case_id)
    if connector_id is not None:
        query = query.where(DataLedgerEntry.connector_id == connector_id)
    query = query.order_by(DataLedgerEntry.id.desc()).limit(limit).offset(offset)
    return list((await session.execute(query)).scalars())


async def list_decision_ledger(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    case_id: UUID | None,
    limit: int,
    offset: int,
) -> list[DecisionLedgerEvent]:
    query = select(DecisionLedgerEvent).where(DecisionLedgerEvent.tenant_id == tenant_id)
    if case_id is not None:
        query = query.where(DecisionLedgerEvent.case_id == case_id)
    query = query.order_by(DecisionLedgerEvent.id.desc()).limit(limit).offset(offset)
    return list((await session.execute(query)).scalars())
