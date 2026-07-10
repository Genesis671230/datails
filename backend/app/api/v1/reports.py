"""Report routes: draft, get, versions, approve (human gate)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.core.errors import AppError
from app.schemas.reports import (
    ReportDraftRequest,
    ReportDraftResponse,
    ReportOut,
    ReportVersionOut,
)
from app.services.reports import service as reports_service

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


@router.post("/reports/draft", response_model=ReportDraftResponse, status_code=201)
async def draft_report(
    body: ReportDraftRequest, ctx: Ctx, session: DbSession
) -> ReportDraftResponse:
    try:
        report, version = await reports_service.draft_report(
            session,
            ctx.tenant_id,
            ctx.user.id,
            case_id=body.case_id,
            report_type=body.report_type,
            title=body.title,
            jurisdiction=body.jurisdiction,
            instructions=body.instructions,
        )
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    return ReportDraftResponse(
        report=ReportOut.model_validate(report),
        version=ReportVersionOut.model_validate(version),
    )


@router.get("/reports/{report_id}", response_model=ReportOut)
async def get_report(report_id: UUID, ctx: Ctx, session: DbSession) -> ReportOut:
    report = await reports_service.get_report(session, ctx.tenant_id, report_id)
    return ReportOut.model_validate(report)


@router.get("/reports/{report_id}/versions", response_model=list[ReportVersionOut])
async def get_versions(
    report_id: UUID, ctx: Ctx, session: DbSession
) -> list[ReportVersionOut]:
    versions = await reports_service.list_versions(session, ctx.tenant_id, report_id)
    return [ReportVersionOut.model_validate(version) for version in versions]


@router.post("/reports/{report_id}/approve", response_model=ReportOut)
async def approve_report(report_id: UUID, ctx: Ctx, session: DbSession) -> ReportOut:
    report = await reports_service.approve_report(
        session, ctx.tenant_id, ctx.user.id, report_id
    )
    return ReportOut.model_validate(report)
