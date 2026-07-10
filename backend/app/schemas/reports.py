"""Request/response schemas for reports."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import ReportStatus, ReportType


class ReportDraftRequest(BaseModel):
    case_id: UUID
    report_type: ReportType
    title: str = Field(min_length=1, max_length=500)
    jurisdiction: str | None = Field(default=None, max_length=10)
    instructions: str | None = Field(default=None, max_length=5000)


class ReportOut(BaseModel):
    id: UUID
    case_id: UUID
    report_type: ReportType
    title: str
    status: ReportStatus
    jurisdiction: str | None
    current_version_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportVersionOut(BaseModel):
    id: UUID
    report_id: UUID
    version_number: int
    content_markdown: str
    source_refs_json: dict | None
    generated_by_ai: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportDraftResponse(BaseModel):
    report: ReportOut
    version: ReportVersionOut
