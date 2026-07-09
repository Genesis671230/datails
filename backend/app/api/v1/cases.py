"""Case domain routes. Thin: validate, resolve context, call service."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.schemas.cases import (
    CaseCreate,
    CaseDetailOut,
    CaseOut,
    CaseUpdate,
    DecisionOut,
    EvidenceCreate,
    EvidenceOut,
    FindingOut,
    WalletAttachRequest,
    WalletOut,
)
from app.services.cases import service as cases_service

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


def _wallet_out(link_wallet_pair) -> WalletOut:
    link, wallet = link_wallet_pair
    out = WalletOut.model_validate(wallet)
    return out.model_copy(update={"role_in_case": link.role_in_case})


def _detail_response(detail: cases_service.CaseDetail) -> CaseDetailOut:
    base = CaseOut.model_validate(detail.case)
    return CaseDetailOut(
        **base.model_dump(),
        metadata=detail.case.metadata_json,
        wallets=[_wallet_out(pair) for pair in detail.wallets],
        evidence=[EvidenceOut.model_validate(item) for item in detail.evidence],
        findings=[FindingOut.model_validate(finding) for finding in detail.findings],
        decisions=[DecisionOut.model_validate(decision) for decision in detail.decisions],
    )


@router.post("/cases", response_model=CaseOut, status_code=201)
async def create_case(body: CaseCreate, ctx: Ctx, session: DbSession) -> CaseOut:
    case = await cases_service.create_case(session, ctx.tenant_id, ctx.user.id, body)
    return CaseOut.model_validate(case)


@router.get("/cases", response_model=list[CaseOut])
async def list_cases(
    ctx: Ctx,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CaseOut]:
    cases = await cases_service.list_tenant_cases(
        session, ctx.tenant_id, limit=limit, offset=offset
    )
    return [CaseOut.model_validate(case) for case in cases]


@router.get("/cases/{case_id}", response_model=CaseDetailOut)
async def get_case(case_id: UUID, ctx: Ctx, session: DbSession) -> CaseDetailOut:
    detail = await cases_service.get_case_detail(session, ctx.tenant_id, case_id)
    return _detail_response(detail)


@router.put("/cases/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: UUID, body: CaseUpdate, ctx: Ctx, session: DbSession
) -> CaseOut:
    case = await cases_service.update_case(session, ctx.tenant_id, case_id, body)
    return CaseOut.model_validate(case)


@router.post("/cases/{case_id}/wallets", response_model=WalletOut, status_code=201)
async def attach_wallet(
    case_id: UUID, body: WalletAttachRequest, ctx: Ctx, session: DbSession
) -> WalletOut:
    link, wallet = await cases_service.attach_wallet(
        session, ctx.tenant_id, ctx.user.id, case_id, body
    )
    return _wallet_out((link, wallet))


@router.post("/cases/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
async def add_evidence(
    case_id: UUID, body: EvidenceCreate, ctx: Ctx, session: DbSession
) -> EvidenceOut:
    evidence = await cases_service.add_evidence(session, ctx.tenant_id, case_id, body)
    return EvidenceOut.model_validate(evidence)
