"""Connector models: connectors, connector_runs.

Block C (connector execution layer). Columns per 03 Phase 4, amended by
LD-11 (no calls_today counter — daily usage is derived from connector_runs)
and LD-22 (credential_owner). Secrets never live here: `secret_ref` is a
Key Vault reference only.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    ConnectorRunStatus,
    ConnectorStatus,
    ConnectorType,
    CredentialOwner,
)


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Connector(Base):
    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    connector_type: Mapped[ConnectorType] = mapped_column(_enum(ConnectorType, "connector_type"))
    base_url: Mapped[str | None] = mapped_column(String(1000))
    auth_type: Mapped[str | None] = mapped_column(String(50))
    # Key Vault secret reference — never a raw secret (01 §3, 02 Block C).
    secret_ref: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ConnectorStatus] = mapped_column(
        _enum(ConnectorStatus, "connector_status"), default=ConnectorStatus.ACTIVE
    )
    # Configuration only; enforcement derives usage from connector_runs (LD-11).
    daily_call_limit: Mapped[int | None] = mapped_column(Integer)
    # LD-22: pilot Crystal key is Datails-shared; tenants can bring their own.
    credential_owner: Mapped[CredentialOwner] = mapped_column(
        _enum(CredentialOwner, "credential_owner"), default=CredentialOwner.TENANT
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConnectorRun(Base):
    __tablename__ = "connector_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    connector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connectors.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ConnectorRunStatus] = mapped_column(
        _enum(ConnectorRunStatus, "connector_run_status"),
        default=ConnectorRunStatus.PENDING,
    )
    request_ref: Mapped[str | None] = mapped_column(String(1000))
    response_ref: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
