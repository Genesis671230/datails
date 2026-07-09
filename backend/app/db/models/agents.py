"""Workflow agent models: workflow_agents, workflow_agent_runs.

Block G (AI orchestration). Named workflow_agents in code per LD-21
("Digital Colleagues" is external copy only). Runs are resumable state
machines (LD-27): interrupted runs resume from the last confirmed step,
never re-executing confirmed work.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AgentType, RunStatus


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class WorkflowAgent(Base):
    __tablename__ = "workflow_agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    agent_type: Mapped[AgentType] = mapped_column(_enum(AgentType, "agent_type"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    role_instructions: Mapped[str | None] = mapped_column(Text)
    allowed_tools_json: Mapped[dict | None] = mapped_column(JSONB)
    allowed_actions_json: Mapped[dict | None] = mapped_column(JSONB)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WorkflowAgentRun(Base):
    __tablename__ = "workflow_agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    workflow_agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflow_agents.id"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), index=True)
    task_type: Mapped[str] = mapped_column(String(100))
    input_ref_json: Mapped[dict | None] = mapped_column(JSONB)
    output_ref_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[RunStatus] = mapped_column(
        _enum(RunStatus, "run_status"), default=RunStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
