"""Append-only ledger models: data_ledger, decision_ledger, ai_call_log,
learning_events.

Blocks E/F (provenance and audit). These tables are insert-only at the
database level (LD-3, LD-30): the application role holds INSERT+SELECT only,
and triggers reject UPDATE/DELETE as defense in depth. Both mechanisms are
created in the same migration as the tables. Cross-entry hash chaining is
deferred (DECISIONS.md); per-entry SHA-256 payload_hash is mandatory now.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DecisionLedgerEventType, LearningEventType

# Tables under LD-3 insert-only enforcement; the migration and its tests
# iterate this list.
APPEND_ONLY_TABLES = ("data_ledger", "decision_ledger", "ai_call_log", "learning_events")


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class DataLedgerEntry(Base):
    __tablename__ = "data_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), index=True)
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("connectors.id"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(100))
    source_ref: Mapped[str | None] = mapped_column(String(1000))
    # SHA-256 of the raw payload (LD-3/LD-4).
    payload_hash: Mapped[str] = mapped_column(String(64))
    storage_ref: Mapped[str] = mapped_column(String(1000))
    retrieved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DecisionLedgerEvent(Base):
    __tablename__ = "decision_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"), index=True)
    event_type: Mapped[DecisionLedgerEventType] = mapped_column(
        _enum(DecisionLedgerEventType, "decision_ledger_event_type")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_type: Mapped[str] = mapped_column(String(50))
    inputs_ref_json: Mapped[dict | None] = mapped_column(JSONB)
    approved: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AiCallLogEntry(Base):
    __tablename__ = "ai_call_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), index=True)
    workflow_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_agents.id"), index=True
    )
    task_type: Mapped[str] = mapped_column(String(100))
    model_name: Mapped[str] = mapped_column(String(100))
    tool_refs_json: Mapped[dict | None] = mapped_column(JSONB)
    prompt_hash: Mapped[str] = mapped_column(String(64))
    response_hash: Mapped[str | None] = mapped_column(String(64))
    token_input: Mapped[int | None] = mapped_column(Integer)
    token_output: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cases.id"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[LearningEventType] = mapped_column(
        _enum(LearningEventType, "learning_event_type")
    )
    # What the event is about: report, trace, hop, run… (05 §9).
    subject_type: Mapped[str] = mapped_column(String(100))
    subject_id: Mapped[str] = mapped_column(String(100))
    # Deltas, durations, edit sizes — no raw case content duplication (05 §9).
    payload_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
