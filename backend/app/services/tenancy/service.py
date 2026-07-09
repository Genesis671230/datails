"""Tenancy service: workspace bootstrap and current-context resolution.

Bootstrap is the ONLY provisioning path (LD-1): on the first authenticated
request from an unknown Entra `oid`, the frontend calls
POST /api/v1/workspaces/bootstrap and this service creates
tenant → user (owner) → default workspace → onboarding session.
Repeat calls are idempotent: an existing user gets their current context back.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthClaims
from app.core.errors import NotFoundError
from app.core.logging import get_logger, log_fields
from app.db.models import OnboardingSession, Tenant, User, Workspace
from app.db.models.enums import UserRole
from app.db.repositories.tenancy import (
    get_default_workspace,
    get_latest_onboarding_session,
    get_tenant,
    slug_exists,
)
from app.db.repositories.users import get_user_by_oid
from app.services.methodologies.baseline_seed import seed_baseline_methodology

logger = get_logger(__name__)

DEFAULT_WORKSPACE_NAME = "Crypto Investigations"


@dataclass(frozen=True)
class TenantContext:
    tenant: Tenant
    user: User
    workspace: Workspace
    onboarding_status: str | None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tenant"


async def _unique_slug(session: AsyncSession, base: str) -> str:
    slug = _slugify(base)
    if not await slug_exists(session, slug):
        return slug
    return f"{slug}-{uuid.uuid4().hex[:6]}"


async def bootstrap_workspace(
    session: AsyncSession, claims: AuthClaims, tenant_name: str | None = None
) -> TenantContext:
    """Create tenant, owner user, default workspace, and onboarding session for
    an unknown oid; return the existing context for a known one."""
    existing = await get_user_by_oid(session, claims.oid)
    if existing is not None:
        existing.last_login_at = datetime.now(UTC)
        await session.commit()
        return await resolve_context(session, claims.oid)

    name = tenant_name or (claims.email or "workspace").split("@")[0]
    tenant = Tenant(slug=await _unique_slug(session, name), name=name)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        external_auth_id=claims.oid,
        email=claims.email or "",
        display_name=claims.name,
        role=UserRole.OWNER,
        last_login_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()

    workspace = Workspace(tenant_id=tenant.id, name=DEFAULT_WORKSPACE_NAME, is_default=True)
    session.add(workspace)
    await session.flush()
    onboarding = OnboardingSession(tenant_id=tenant.id, user_id=user.id)
    session.add(onboarding)
    # Every new tenant starts with the AQ baseline methodology (05 §2) — the
    # workspace must not feel like an empty engine.
    await seed_baseline_methodology(session, tenant.id, workspace.id)
    await session.commit()

    logger.info(
        "bootstrapped tenant %s for oid %s",
        tenant.slug,
        claims.oid,
        extra=log_fields(module="tenancy", action="bootstrap", status="created"),
    )
    return TenantContext(
        tenant=tenant,
        user=user,
        workspace=workspace,
        onboarding_status=onboarding.status.value,
    )


async def resolve_context(session: AsyncSession, oid: str) -> TenantContext:
    """Return the full tenant context for a known oid (GET /workspaces/me)."""
    user = await get_user_by_oid(session, oid)
    if user is None:
        raise NotFoundError("No workspace for this identity. Call bootstrap first.")
    tenant = await get_tenant(session, user.tenant_id)
    workspace = await get_default_workspace(session, user.tenant_id)
    if tenant is None or workspace is None:
        raise NotFoundError("Tenant context is incomplete.")
    onboarding = await get_latest_onboarding_session(session, tenant.id, user.id)
    return TenantContext(
        tenant=tenant,
        user=user,
        workspace=workspace,
        onboarding_status=onboarding.status.value if onboarding else None,
    )
