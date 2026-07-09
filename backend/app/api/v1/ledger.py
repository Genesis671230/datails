"""Ledger read routes (LD-8): provenance must be visible in the pilot,
not just stored. Tenant-scoped, read-only, newest first."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.db.repositories.ledgers import list_data_ledger, list_decision_ledger
from app.schemas.decisions import DataLedgerEntryOut, DecisionLedgerEventOut

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/ledger/data", response_model=list[DataLedgerEntryOut])
async def get_data_ledger(
    ctx: Ctx,
    session: DbSession,
    case_id: UUID | None = None,
    connector_id: UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[DataLedgerEntryOut]:
    entries = await list_data_ledger(
        session, ctx.tenant_id, case_id=case_id, connector_id=connector_id,
        limit=limit, offset=offset,
    )
    return [DataLedgerEntryOut.model_validate(entry) for entry in entries]


@router.get("/ledger/decision", response_model=list[DecisionLedgerEventOut])
async def get_decision_ledger(
    ctx: Ctx,
    session: DbSession,
    case_id: UUID | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> list[DecisionLedgerEventOut]:
    events = await list_decision_ledger(
        session, ctx.tenant_id, case_id=case_id, limit=limit, offset=offset
    )
    return [DecisionLedgerEventOut.model_validate(event) for event in events]
