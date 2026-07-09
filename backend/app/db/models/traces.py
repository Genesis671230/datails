"""Fund-flow trace models: traces, trace_hops (05 §8).

The pilot's demonstrable loop: FIFO attribution is deterministic engine work
under per-hop human confirmation — never autonomous tracing. Hot-wallet
boundaries end traversal and propose an exchange information request instead.
A hop confirmation writes a decision_ledger event in the same transaction
(LD-9 pattern); the agent never proposes past an unconfirmed hop.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import AttributionMethod, BoundaryFlag, RunStatus, TraceHopStatus


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    # Where the stolen funds start.
    root_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    # Attribution is configuration, not rebuild (05 §8).
    attribution_method: Mapped[AttributionMethod] = mapped_column(
        _enum(AttributionMethod, "attribution_method"), default=AttributionMethod.FIFO
    )
    status: Mapped[RunStatus] = mapped_column(
        _enum(RunStatus, "run_status"), default=RunStatus.PENDING
    )
    workflow_agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflow_agent_runs.id")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TraceHop(Base):
    __tablename__ = "trace_hops"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("traces.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    hop_index: Mapped[int] = mapped_column(Integer)
    from_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    to_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"))
    tx_hash: Mapped[str] = mapped_column(String(255))
    asset: Mapped[str] = mapped_column(String(50))
    chain: Mapped[str] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Numeric(36, 18))
    # Per-hop confidence, surfaced to the investigator (05 §8).
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    # data_ledger references grounding this hop (labels, Crystal payloads).
    evidence_refs_json: Mapped[dict | None] = mapped_column(JSONB)
    # Human-judgment boundaries from operator evidence [02-16].
    boundary_flag: Mapped[BoundaryFlag | None] = mapped_column(
        _enum(BoundaryFlag, "boundary_flag")
    )
    status: Mapped[TraceHopStatus] = mapped_column(
        _enum(TraceHopStatus, "trace_hop_status"), default=TraceHopStatus.PROPOSED
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
