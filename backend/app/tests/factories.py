"""Minimal object factories for tests.

Build the tenant → user → workspace → case chain that most domain rows hang
off. Plain functions, no factory framework — explicit over clever.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Case, Tenant, User, Workspace
from app.db.models.enums import CaseType, UserRole


async def create_tenant(session: AsyncSession, *, slug: str | None = None) -> Tenant:
    suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(slug=slug or f"tenant-{suffix}", name=f"Tenant {suffix}")
    session.add(tenant)
    await session.flush()
    return tenant


async def create_user(
    session: AsyncSession,
    tenant: Tenant,
    *,
    role: UserRole = UserRole.OWNER,
    oid: str | None = None,
) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        tenant_id=tenant.id,
        external_auth_id=oid or str(uuid.uuid4()),
        email=f"user-{suffix}@example.test",
        display_name=f"User {suffix}",
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


async def create_workspace(session: AsyncSession, tenant: Tenant) -> Workspace:
    workspace = Workspace(tenant_id=tenant.id, name="Crypto Investigations", is_default=True)
    session.add(workspace)
    await session.flush()
    return workspace


async def create_case(
    session: AsyncSession, tenant: Tenant, workspace: Workspace, user: User
) -> Case:
    case = Case(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        created_by=user.id,
        title="Test case",
        case_type=CaseType.CRIMINAL_INVESTIGATION,
    )
    session.add(case)
    await session.flush()
    return case


async def create_tenant_chain(session: AsyncSession) -> tuple[Tenant, User, Workspace, Case]:
    tenant = await create_tenant(session)
    user = await create_user(session, tenant)
    workspace = await create_workspace(session, tenant)
    case = await create_case(session, tenant, workspace, user)
    return tenant, user, workspace, case
