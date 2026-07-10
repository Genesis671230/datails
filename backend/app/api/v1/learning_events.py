"""Learning-event ingestion route (LD-30; founder decision, 10 Jul 2026).

The minimal frontend-contract surface for user actions the backend cannot
observe directly (assistant accept/reject, report edits). Validated against
the 05 §9 vocabulary, tenant-scoped, and consent-gated exactly like the
server-side capture points: without `learning_capture_enabled` the request
is acknowledged but nothing is stored, and the response says so honestly.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.core.errors import NotFoundError
from app.db.models.enums import LearningEventType
from app.db.repositories.cases import get_case
from app.db.repositories.tenancy import get_default_workspace
from app.services.ledgers.learning import capture_learning_event

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]

MAX_SUBJECT_LENGTH = 100


class LearningEventIn(BaseModel):
    event_type: LearningEventType
    subject_type: str = Field(min_length=1, max_length=MAX_SUBJECT_LENGTH)
    subject_id: str = Field(min_length=1, max_length=MAX_SUBJECT_LENGTH)
    case_id: UUID | None = None
    # Deltas, durations, edit sizes — no raw case content (05 §9).
    payload: dict | None = None


class LearningEventResult(BaseModel):
    captured: bool
    event_id: int | None = None


@router.post("/learning-events", response_model=LearningEventResult, status_code=201)
async def ingest_learning_event(
    body: LearningEventIn, ctx: Ctx, session: DbSession
) -> LearningEventResult:
    workspace = await get_default_workspace(session, ctx.tenant_id)
    if workspace is None:
        raise NotFoundError("Tenant has no default workspace.")
    if body.case_id is not None:
        case = await get_case(session, ctx.tenant_id, body.case_id)
        if case is None:
            raise NotFoundError("Case not found.")

    event = await capture_learning_event(
        session,
        tenant_id=ctx.tenant_id,
        workspace_id=workspace.id,
        case_id=body.case_id,
        actor_id=ctx.user.id,
        event_type=body.event_type,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        payload=body.payload,
    )
    await session.commit()
    if event is None:
        return LearningEventResult(captured=False)
    return LearningEventResult(captured=True, event_id=event.id)
