"""Case-aware assistant route (LD-20) — the "chat with your connected case
data" surface, case-attached by construction."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.services.ai.model_router import TASK_TYPES
from app.services.ai.task_executor import execute_case_task

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


class AssistantRequest(BaseModel):
    case_id: UUID
    task_type: str = Field(default="research_assistant")
    input: str = Field(min_length=1, max_length=10_000)


class AssistantResponse(BaseModel):
    case_id: UUID
    task_type: str
    output: str
    model: str
    source_refs: list[str]
    ai_call_log_id: int


@router.post("/ai/assistant", response_model=AssistantResponse)
async def assistant(body: AssistantRequest, ctx: Ctx, session: DbSession) -> AssistantResponse:
    from app.core.errors import AppError

    if body.task_type not in TASK_TYPES:
        raise AppError(f"unknown task_type; allowed: {sorted(TASK_TYPES)}")
    result = await execute_case_task(
        session,
        tenant_id=ctx.tenant_id,
        case_id=body.case_id,
        task_type=body.task_type,
        user_input=body.input,
    )
    return AssistantResponse(
        case_id=body.case_id,
        task_type=body.task_type,
        output=result.text,
        model=result.model,
        source_refs=result.source_refs,
        ai_call_log_id=result.ai_call_log_id,
    )
