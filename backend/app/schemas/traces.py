"""Request/response schemas for the trace loop."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.db.models.enums import (
    AttributionMethod,
    BoundaryFlag,
    RunStatus,
    TraceHopStatus,
)


class TraceCreateRequest(BaseModel):
    root_wallet_id: UUID


class TraceHopOut(BaseModel):
    id: UUID
    hop_index: int
    from_wallet_id: UUID
    to_wallet_id: UUID
    tx_hash: str
    asset: str
    chain: str
    amount: Decimal
    confidence: Decimal
    evidence_refs_json: dict | None
    boundary_flag: BoundaryFlag | None
    status: TraceHopStatus
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TraceOut(BaseModel):
    id: UUID
    case_id: UUID
    root_wallet_id: UUID
    attribution_method: AttributionMethod
    status: RunStatus
    workflow_agent_run_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TraceDetailOut(TraceOut):
    hops: list[TraceHopOut]
    # Recommendation + transitions from the workflow agent run (LD-27).
    run_output: dict | None
    # Transaction-explorer graph: nodes with labels+provenance, confirmed
    # edges with confidence (07 Slice 3).
    graph: dict
