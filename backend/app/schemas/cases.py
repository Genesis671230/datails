"""Request/response schemas for the case domain."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import (
    CasePriority,
    CaseStatus,
    CaseType,
    CaseWalletRole,
    EvidenceType,
    FindingType,
    WalletKind,
)

MAX_TITLE_LENGTH = 500


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    case_type: CaseType
    priority: CasePriority = CasePriority.MEDIUM
    summary: str | None = None
    metadata: dict | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    summary: str | None = None
    metadata: dict | None = None


class CaseOut(BaseModel):
    id: UUID
    title: str
    case_type: CaseType
    status: CaseStatus
    priority: CasePriority
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletAttachRequest(BaseModel):
    address: str = Field(min_length=1, max_length=255)
    chain: str = Field(min_length=1, max_length=50)
    wallet_kind: WalletKind | None = None
    role_in_case: CaseWalletRole | None = None


class WalletOut(BaseModel):
    id: UUID
    address: str
    chain: str
    wallet_kind: WalletKind | None
    is_watched: bool
    role_in_case: CaseWalletRole | None = None

    model_config = {"from_attributes": True}


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    storage_ref: str | None = Field(default=None, max_length=1000)
    source_ref: str | None = Field(default=None, max_length=1000)
    metadata: dict | None = None


class EvidenceOut(BaseModel):
    id: UUID
    evidence_type: EvidenceType
    title: str
    storage_ref: str | None
    source_ref: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingCreate(BaseModel):
    case_id: UUID
    finding_type: FindingType
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    content: str | None = None
    source_ref: str | None = Field(default=None, max_length=1000)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class FindingOut(BaseModel):
    id: UUID
    case_id: UUID
    finding_type: FindingType
    title: str
    content: str | None
    source_ref: str | None
    confidence: Decimal | None
    is_ai_generated: bool
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DecisionOut(BaseModel):
    id: UUID
    case_id: UUID
    decision_type: str
    description: str
    rationale: str | None
    outcome: str | None
    made_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDetailOut(CaseOut):
    """Coherent case state: LD-8 requires findings and decisions explicitly."""

    metadata: dict | None = None
    wallets: list[WalletOut]
    evidence: list[EvidenceOut]
    findings: list[FindingOut]
    decisions: list[DecisionOut]
