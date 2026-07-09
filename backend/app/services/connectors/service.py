"""Connector registry service: register, list, test.

The test call verifies secret resolution and transport status only — it
persists NOTHING durable (LD-18.2: no blob, no ledger entry, no run row).
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.db.models import Connector
from app.db.models.enums import ConnectorType
from app.db.repositories.tenancy import get_default_workspace
from app.integrations.factories import get_secret_resolver
from app.integrations.key_vault.base import SecretResolutionError
from app.schemas.connectors import REGISTRABLE_TYPES, ConnectorCreate, ConnectorTestResult


class ConnectorTypeNotRegistrableError(Exception):
    pass


async def register_connector(
    session: AsyncSession, tenant_id: UUID, data: ConnectorCreate
) -> Connector:
    if data.connector_type not in REGISTRABLE_TYPES:
        raise ConnectorTypeNotRegistrableError(
            f"connector type {data.connector_type.value!r} is not registrable in Phase 1 "
            f"(LD-19/LD-22); registrable: {[t.value for t in REGISTRABLE_TYPES]}"
        )
    workspace = await get_default_workspace(session, tenant_id)
    if workspace is None:
        raise NotFoundError("Tenant has no default workspace.")
    connector = Connector(
        tenant_id=tenant_id,
        workspace_id=workspace.id,
        name=data.name,
        connector_type=data.connector_type,
        base_url=data.base_url,
        auth_type=data.auth_type,
        secret_ref=data.secret_ref,
        daily_call_limit=data.daily_call_limit,
        credential_owner=data.credential_owner,
        metadata_json=data.metadata,
    )
    session.add(connector)
    await session.commit()
    return connector


async def list_connectors(session: AsyncSession, tenant_id: UUID) -> list[Connector]:
    result = await session.execute(
        select(Connector)
        .where(Connector.tenant_id == tenant_id)
        .order_by(Connector.created_at)
    )
    return list(result.scalars())


async def get_connector(
    session: AsyncSession, tenant_id: UUID, connector_id: UUID
) -> Connector:
    result = await session.execute(
        select(Connector).where(
            Connector.id == connector_id, Connector.tenant_id == tenant_id
        )
    )
    connector = result.scalar_one_or_none()
    if connector is None:
        raise NotFoundError("Connector not found.")
    return connector


async def get_active_connector_by_type(
    session: AsyncSession, tenant_id: UUID, connector_type: ConnectorType
) -> Connector:
    result = await session.execute(
        select(Connector)
        .where(
            Connector.tenant_id == tenant_id,
            Connector.connector_type == connector_type,
            Connector.status == "active",
        )
        .order_by(Connector.created_at)
        .limit(1)
    )
    connector = result.scalar_one_or_none()
    if connector is None:
        raise NotFoundError(
            f"No active {connector_type.value} connector registered for this tenant."
        )
    return connector


async def test_connector(
    session: AsyncSession, tenant_id: UUID, connector_id: UUID
) -> ConnectorTestResult:
    """Verify secret resolution and report transport status. Persists nothing
    (LD-18.2)."""
    connector = await get_connector(session, tenant_id, connector_id)

    secret_resolved = False
    detail = "no secret_ref configured"
    if connector.secret_ref:
        try:
            await get_secret_resolver().get_secret(connector.secret_ref)
            secret_resolved = True
            detail = "secret resolved"
        except SecretResolutionError as exc:
            detail = str(exc)

    transport = "n/a"
    if connector.connector_type == ConnectorType.CRYSTAL:
        transport = get_settings().crystal_transport
        if transport == "replay":
            detail += "; replay transport serves recorded fixtures (live gated on LD-6 spike)"
    return ConnectorTestResult(
        connector_id=connector.id,
        secret_resolved=secret_resolved,
        transport=transport,
        detail=detail,
    )
