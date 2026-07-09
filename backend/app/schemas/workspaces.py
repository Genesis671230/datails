"""Request/response schemas for workspace routes."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import UserRole


class BootstrapRequest(BaseModel):
    tenant_name: str | None = Field(default=None, max_length=255)


class TenantOut(BaseModel):
    id: UUID
    slug: str
    name: str
    plan: str
    region: str
    learning_capture_enabled: bool

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    role: UserRole

    model_config = {"from_attributes": True}


class WorkspaceOut(BaseModel):
    id: UUID
    name: str
    workspace_type: str
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceContextResponse(BaseModel):
    tenant: TenantOut
    user: UserOut
    workspace: WorkspaceOut
    onboarding_status: str | None
