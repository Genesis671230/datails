"""Learning-event capture (LD-30, 05 §9).

Append-only capture of how investigators work — CONSENT-GATED: the capture
point checks `tenants.learning_capture_enabled` (default false; set true only
when the cohort member's Data & Methodology Permission is signed). Capturing
without the flag is a defect, not a shortcut. Capture only — no analytics in
the pilot.

Payloads carry deltas/durations/sizes — never raw case content duplication.
Writers add to the caller's transaction (LD-9 pattern) so the event commits
with the action it describes.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, log_fields
from app.db.models import LearningEvent, Tenant
from app.db.models.enums import LearningEventType

logger = get_logger(__name__)


async def capture_learning_event(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    case_id: UUID | None,
    actor_id: UUID | None,
    event_type: LearningEventType,
    subject_type: str,
    subject_id: str,
    payload: dict | None = None,
) -> LearningEvent | None:
    """Capture one event IF the tenant has consented; otherwise a no-op.

    Does not commit — joins the caller's transaction.
    """
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None or not tenant.learning_capture_enabled:
        return None

    event = LearningEvent(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        case_id=case_id,
        actor_id=actor_id,
        event_type=event_type,
        subject_type=subject_type,
        subject_id=subject_id,
        payload_json=payload,
    )
    session.add(event)
    await session.flush()
    logger.info(
        "learning event captured",
        extra=log_fields(
            module="learning",
            action=event_type.value,
            status="ok",
            case_id=str(case_id) if case_id else None,
        ),
    )
    return event
