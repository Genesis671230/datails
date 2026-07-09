"""Request/response schemas for the connector layer.

Mode names risk_check / full_investigation are Datails product terms (LD-22),
not vendor API claims — they are part of the generic contract.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import (
    ConnectorStatus,
    ConnectorType,
    CredentialOwner,
    RiskColor,
    WalletLabelType,
)

ConnectorMode = Literal["risk_check", "full_investigation"]

# Registrable in Phase 1 (LD-19): generic_api is the mock/base type only;
# mcp_server is reserved (LD-22, post-pilot Connector Platform milestone).
REGISTRABLE_TYPES = (
    ConnectorType.CRYSTAL,
    ConnectorType.BLOCKCHAIN_EXPLORER,
    ConnectorType.FILE_UPLOAD,
)


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: ConnectorType
    base_url: str | None = Field(default=None, max_length=1000)
    auth_type: str | None = Field(default=None, max_length=50)
    secret_ref: str | None = Field(default=None, max_length=500)
    daily_call_limit: int | None = Field(default=None, ge=1)
    credential_owner: CredentialOwner = CredentialOwner.TENANT
    metadata: dict | None = None


class ConnectorOut(BaseModel):
    id: UUID
    name: str
    connector_type: ConnectorType
    base_url: str | None
    auth_type: str | None
    secret_ref: str | None
    status: ConnectorStatus
    daily_call_limit: int | None
    credential_owner: CredentialOwner
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectorTestResult(BaseModel):
    connector_id: UUID
    secret_resolved: bool
    transport: str
    detail: str


class WalletLookupRequest(BaseModel):
    address: str = Field(min_length=1, max_length=255)
    chain: str = Field(min_length=1, max_length=50)
    mode: ConnectorMode = "risk_check"


class WalletLookupAndAttachRequest(WalletLookupRequest):
    case_id: UUID
    role_in_case: str | None = None


class LabelOut(BaseModel):
    label: str
    label_type: WalletLabelType
    risk_color: RiskColor | None
    confidence: Decimal | None


class TransferOut(BaseModel):
    tx_hash: str
    direction: str
    counterparty_address: str
    asset: str
    amount: str
    timestamp: str | None


class WalletLookupResponse(BaseModel):
    connector_run_id: UUID
    data_ledger_id: int
    payload_hash: str
    storage_ref: str
    address: str | None
    chain: str | None
    risk_score: float | None
    risk_color: RiskColor | None
    labels: list[LabelOut]
    transfers: list[TransferOut]
    wallet_id: UUID | None = None
    case_id: UUID | None = None
