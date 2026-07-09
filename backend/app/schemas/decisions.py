"""Request/response schemas for decisions and ledger reads."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import DecisionLedgerEventType, DecisionType


class DecisionCreate(BaseModel):
    case_id: UUID
    decision_type: DecisionType
    description: str = Field(min_length=1)
    rationale: str | None = None
    inputs_ref: dict | None = None
    outcome: str | None = Field(default=None, max_length=500)


class DataLedgerEntryOut(BaseModel):
    id: int
    case_id: UUID | None
    connector_id: UUID | None
    source_type: str
    source_ref: str | None
    payload_hash: str
    storage_ref: str
    retrieved_by_user_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionLedgerEventOut(BaseModel):
    id: int
    case_id: UUID
    decision_id: UUID | None
    event_type: DecisionLedgerEventType
    actor_id: UUID | None
    actor_type: str
    approved: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}
