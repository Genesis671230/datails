"""Decisions service.

LD-9 source-of-truth rule: `decisions` holds current decision objects;
`decision_ledger` is the immutable event history. Every decision write
appends its ledger event in the SAME database transaction — one commit for
both rows. Decisions are never hard-deleted; changes are supersessions
(later slices).
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.logging import get_logger, log_fields
from app.db.models import Decision
from app.db.models.enums import DecisionLedgerEventType
from app.db.repositories.cases import get_case
from app.schemas.decisions import DecisionCreate
from app.services.ledgers.writers import write_decision_event

logger = get_logger(__name__)

ACTOR_TYPE_USER = "user"


async def create_decision(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, data: DecisionCreate
) -> Decision:
    case = await get_case(session, tenant_id, data.case_id)
    if case is None:
        raise NotFoundError("Case not found.")

    decision = Decision(
        case_id=data.case_id,
        tenant_id=tenant_id,
        made_by=user_id,
        decision_type=data.decision_type,
        description=data.description,
        rationale=data.rationale,
        inputs_ref_json=data.inputs_ref,
        outcome=data.outcome,
    )
    session.add(decision)
    await session.flush()

    # LD-9: same transaction, no separate commit.
    await write_decision_event(
        session,
        tenant_id=tenant_id,
        workspace_id=case.workspace_id,
        case_id=data.case_id,
        decision_id=decision.id,
        event_type=DecisionLedgerEventType.CREATED,
        actor_id=user_id,
        actor_type=ACTOR_TYPE_USER,
        inputs_ref=data.inputs_ref,
    )
    await session.commit()
    logger.info(
        "decision created with ledger event",
        extra=log_fields(
            module="decisions", action="create", status="ok", case_id=str(data.case_id)
        ),
    )
    return decision
