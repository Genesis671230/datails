"""Connector routes: registry, test, and Crystal wallet lookup.

The /connectors/crystal/* paths are the spec's canonical route names; the
handlers stay vendor-agnostic — they call generic services with
ConnectorType.CRYSTAL. No Crystal-specific module is imported here
(genericity criterion).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.core.errors import AppError
from app.db.models.enums import ConnectorType
from app.schemas.connectors import (
    ConnectorCreate,
    ConnectorOut,
    ConnectorTestResult,
    LabelOut,
    TransferOut,
    WalletLookupAndAttachRequest,
    WalletLookupRequest,
    WalletLookupResponse,
)
from app.services.connectors import service as connectors_service
from app.services.connectors.execution import ExecutionOutcome
from app.services.connectors.service import ConnectorTypeNotRegistrableError
from app.services.connectors.wallet_lookup import wallet_lookup, wallet_lookup_and_attach

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


class NotRegistrableError(AppError):
    status_code = 422
    code = "connector_type_not_registrable"


def _lookup_response(
    outcome: ExecutionOutcome, *, wallet_id: UUID | None = None, case_id: UUID | None = None
) -> WalletLookupResponse:
    result = outcome.result
    return WalletLookupResponse(
        connector_run_id=outcome.run.id,
        data_ledger_id=outcome.ledger_entry.id,
        payload_hash=outcome.ledger_entry.payload_hash,
        storage_ref=outcome.ledger_entry.storage_ref,
        address=result.address,
        chain=result.chain,
        risk_score=result.risk_score,
        risk_color=result.risk_color,
        labels=[LabelOut(**vars(label)) for label in result.labels],
        transfers=[TransferOut(**vars(transfer)) for transfer in result.transfers],
        wallet_id=wallet_id,
        case_id=case_id,
    )


@router.post("/connectors", response_model=ConnectorOut, status_code=201)
async def register_connector(
    body: ConnectorCreate, ctx: Ctx, session: DbSession
) -> ConnectorOut:
    try:
        connector = await connectors_service.register_connector(session, ctx.tenant_id, body)
    except ConnectorTypeNotRegistrableError as exc:
        raise NotRegistrableError(str(exc)) from exc
    return ConnectorOut.model_validate(connector)


@router.get("/connectors", response_model=list[ConnectorOut])
async def list_connectors(ctx: Ctx, session: DbSession) -> list[ConnectorOut]:
    connectors = await connectors_service.list_connectors(session, ctx.tenant_id)
    return [ConnectorOut.model_validate(connector) for connector in connectors]


@router.post("/connectors/{connector_id}/test", response_model=ConnectorTestResult)
async def test_connector(
    connector_id: UUID, ctx: Ctx, session: DbSession
) -> ConnectorTestResult:
    return await connectors_service.test_connector(session, ctx.tenant_id, connector_id)


@router.post("/connectors/crystal/wallet-lookup", response_model=WalletLookupResponse)
async def crystal_wallet_lookup(
    body: WalletLookupRequest, ctx: Ctx, session: DbSession
) -> WalletLookupResponse:
    outcome = await wallet_lookup(
        session, ctx.tenant_id, ctx.user.id, ConnectorType.CRYSTAL, body
    )
    return _lookup_response(outcome)


@router.post(
    "/connectors/crystal/wallet-lookup-and-attach", response_model=WalletLookupResponse
)
async def crystal_wallet_lookup_and_attach(
    body: WalletLookupAndAttachRequest, ctx: Ctx, session: DbSession
) -> WalletLookupResponse:
    outcome, wallet = await wallet_lookup_and_attach(
        session, ctx.tenant_id, ctx.user.id, ConnectorType.CRYSTAL, body
    )
    return _lookup_response(outcome, wallet_id=wallet.id, case_id=body.case_id)
