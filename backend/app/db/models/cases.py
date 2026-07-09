"""Case domain models: cases, evidence_items, findings, decisions.

Block D (operational object model). Columns per 03 Phase 5; enums per
05 §1.3/1.3a. Decisions are never hard-deleted — supersession appends a new
row plus a decision_ledger event (LD-9).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    CasePriority,
    CaseStatus,
    CaseType,
    DecisionType,
    EvidenceType,
    FindingType,
)


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(500))
    case_type: Mapped[CaseType] = mapped_column(_enum(CaseType, "case_type"))
    status: Mapped[CaseStatus] = mapped_column(
        _enum(CaseStatus, "case_status"), default=CaseStatus.OPEN
    )
    priority: Mapped[CasePriority] = mapped_column(
        _enum(CasePriority, "case_priority"), default=CasePriority.MEDIUM
    )
    summary: Mapped[str | None] = mapped_column(Text)
    context_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    evidence_type: Mapped[EvidenceType] = mapped_column(_enum(EvidenceType, "evidence_type"))
    title: Mapped[str] = mapped_column(String(500))
    storage_ref: Mapped[str | None] = mapped_column(String(1000))
    source_ref: Mapped[str | None] = mapped_column(String(1000))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    finding_type: Mapped[FindingType] = mapped_column(_enum(FindingType, "finding_type"))
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str | None] = mapped_column(Text)
    source_ref: Mapped[str | None] = mapped_column(String(1000))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    made_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    decision_type: Mapped[DecisionType] = mapped_column(_enum(DecisionType, "decision_type"))
    description: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    inputs_ref_json: Mapped[dict | None] = mapped_column(JSONB)
    outcome: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
