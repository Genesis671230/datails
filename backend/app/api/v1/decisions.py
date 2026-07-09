"""Decisions route."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.schemas.cases import DecisionOut
from app.schemas.decisions import DecisionCreate
from app.services.decisions.service import create_decision

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


@router.post("/decisions", response_model=DecisionOut, status_code=201)
async def post_decision(body: DecisionCreate, ctx: Ctx, session: DbSession) -> DecisionOut:
    decision = await create_decision(session, ctx.tenant_id, ctx.user.id, body)
    return DecisionOut.model_validate(decision)
