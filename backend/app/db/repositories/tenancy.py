"""Tenancy persistence queries: tenants, workspaces, onboarding sessions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OnboardingSession, Tenant, Workspace


async def get_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant | None:
    return await session.get(Tenant, tenant_id)


async def slug_exists(session: AsyncSession, slug: str) -> bool:
    result = await session.execute(select(Tenant.id).where(Tenant.slug == slug))
    return result.scalar_one_or_none() is not None


async def get_default_workspace(session: AsyncSession, tenant_id: UUID) -> Workspace | None:
    result = await session.execute(
        select(Workspace)
        .where(Workspace.tenant_id == tenant_id, Workspace.is_default.is_(True))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_onboarding_session(
    session: AsyncSession, tenant_id: UUID, user_id: UUID
) -> OnboardingSession | None:
    result = await session.execute(
        select(OnboardingSession)
        .where(
            OnboardingSession.tenant_id == tenant_id,
            OnboardingSession.user_id == user_id,
        )
        .order_by(OnboardingSession.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
