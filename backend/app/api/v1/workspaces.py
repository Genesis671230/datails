"""Workspace routes: bootstrap (the only provisioning path, LD-1) and me.

Thin handlers: schema validation, auth claims, service call, response.
"""

from fastapi import APIRouter

from app.api.deps import Claims, DbSession
from app.schemas.workspaces import (
    BootstrapRequest,
    TenantOut,
    UserOut,
    WorkspaceContextResponse,
    WorkspaceOut,
)
from app.services.tenancy.service import TenantContext, bootstrap_workspace, resolve_context

router = APIRouter()


def _to_response(context: TenantContext) -> WorkspaceContextResponse:
    return WorkspaceContextResponse(
        tenant=TenantOut.model_validate(context.tenant),
        user=UserOut.model_validate(context.user),
        workspace=WorkspaceOut.model_validate(context.workspace),
        onboarding_status=context.onboarding_status,
    )


@router.post("/workspaces/bootstrap", response_model=WorkspaceContextResponse)
async def bootstrap(
    body: BootstrapRequest, claims: Claims, session: DbSession
) -> WorkspaceContextResponse:
    context = await bootstrap_workspace(session, claims, tenant_name=body.tenant_name)
    return _to_response(context)


@router.get("/workspaces/me", response_model=WorkspaceContextResponse)
async def me(claims: Claims, session: DbSession) -> WorkspaceContextResponse:
    context = await resolve_context(session, claims.oid)
    return _to_response(context)
