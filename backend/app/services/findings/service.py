"""Findings service.

Findings created by users are human findings (is_ai_generated=false, no
approval needed to exist). AI-generated findings and the approval flow arrive
with the AI layer (Slice 2) — approval is a human gate, never bypassed.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import Finding
from app.db.repositories.cases import get_case
from app.schemas.cases import FindingCreate


async def create_finding(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, data: FindingCreate
) -> Finding:
    case = await get_case(session, tenant_id, data.case_id)
    if case is None:
        raise NotFoundError("Case not found.")
    finding = Finding(
        case_id=data.case_id,
        tenant_id=tenant_id,
        created_by=user_id,
        finding_type=data.finding_type,
        title=data.title,
        content=data.content,
        source_ref=data.source_ref,
        confidence=data.confidence,
        is_ai_generated=False,
    )
    session.add(finding)
    await session.commit()
    return finding
