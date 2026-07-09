"""Findings routes."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.schemas.cases import FindingCreate, FindingOut
from app.services.findings.service import create_finding

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


@router.post("/findings", response_model=FindingOut, status_code=201)
async def post_finding(body: FindingCreate, ctx: Ctx, session: DbSession) -> FindingOut:
    finding = await create_finding(session, ctx.tenant_id, ctx.user.id, body)
    return FindingOut.model_validate(finding)
