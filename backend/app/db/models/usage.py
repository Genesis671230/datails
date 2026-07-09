"""Usage and commercial models: usage_records, tenant_plan_state,
idempotency_keys.

Block I (usage metering — tables exist from Slice 0; metering behavior is a
BACKLOG item per 07) and LD-28 (idempotency on expensive POSTs).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import UsageCategory


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), index=True)
    category: Mapped[UsageCategory] = mapped_column(
        Enum(
            UsageCategory,
            name="usage_category",
            values_callable=lambda e: [m.value for m in e],
        )
    )
    subcategory: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1)
    unit: Mapped[str] = mapped_column(String(50))
    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    ref_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TenantPlanState(Base):
    __tablename__ = "tenant_plan_state"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    current_plan: Mapped[str] = mapped_column(String(50), default="trial")
    usage_limit_json: Mapped[dict | None] = mapped_column(JSONB)
    usage_state_json: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IdempotencyKey(Base):
    """LD-28: replay returns the original response; same key with a different
    payload returns 409. Required on connector runs, workflow-agent runs,
    trace creation, report drafts, and assistant calls."""

    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    route: Mapped[str] = mapped_column(String(255))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_ref: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
