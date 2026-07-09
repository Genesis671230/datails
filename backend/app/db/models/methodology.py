"""Methodology models: methodologies, methodology_steps, generated_templates,
workflow_agent_profiles.

Block B (methodology capture). Columns per 03 Phase 3, amended by LD-19
(generated_templates.jurisdiction_variants_json; integer versioning) and
LD-21 (workflow_agent naming).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AgentType


class Methodology(Base):
    __tablename__ = "methodologies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str | None] = mapped_column(String(255))
    report_style: Mapped[str | None] = mapped_column(String(255))
    jurisdictions_json: Mapped[dict | None] = mapped_column(JSONB)
    trusted_tools_json: Mapped[dict | None] = mapped_column(JSONB)
    # Integer versioning is sufficient for Phase 1 (LD-19).
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MethodologyStep(Base):
    __tablename__ = "methodology_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id"), index=True
    )
    step_order: Mapped[int] = mapped_column(Integer)
    step_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    tool_preference: Mapped[str | None] = mapped_column(String(255))
    output_type: Mapped[str | None] = mapped_column(String(100))
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class GeneratedTemplate(Base):
    __tablename__ = "generated_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id"), index=True
    )
    template_type: Mapped[str] = mapped_column(String(100))
    template_name: Mapped[str] = mapped_column(String(255))
    template_body: Mapped[str] = mapped_column(Text)
    # Jurisdiction wording overlays (LD-19; 05 §1.5: base + variants, not
    # separate templates).
    jurisdiction_variants_json: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WorkflowAgentProfile(Base):
    __tablename__ = "workflow_agent_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id"), index=True
    )
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agent_type", values_callable=lambda e: [m.value for m in e])
    )
    instructions: Mapped[str | None] = mapped_column(Text)
    allowed_tools_json: Mapped[dict | None] = mapped_column(JSONB)
    allowed_outputs_json: Mapped[dict | None] = mapped_column(JSONB)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
