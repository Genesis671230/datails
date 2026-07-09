"""Route dependencies: auth claims and resolved tenant context.

`get_auth_claims` returns the middleware-validated identity. `get_auth_context`
additionally resolves the user row and binds tenant identifiers into the
logging context. Tenant context derives only from the validated token (LD-1).
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthClaims
from app.core.errors import AuthenticationError
from app.core.logging import actor_id_var, tenant_id_var
from app.db.models import User
from app.db.repositories.users import get_user_by_oid
from app.db.session import get_db_session


@dataclass(frozen=True)
class AuthContext:
    user: User
    tenant_id: UUID


def get_auth_claims(request: Request) -> AuthClaims:
    claims = getattr(request.state, "auth_claims", None)
    if claims is None:
        raise AuthenticationError("Request has no validated identity.")
    return claims


Claims = Annotated[AuthClaims, Depends(get_auth_claims)]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_auth_context(claims: Claims, session: DbSession) -> AuthContext:
    user = await get_user_by_oid(session, claims.oid)
    if user is None or not user.is_active:
        raise AuthenticationError("Unknown identity. Call /workspaces/bootstrap first.")
    tenant_id_var.set(str(user.tenant_id))
    actor_id_var.set(str(user.id))
    return AuthContext(user=user, tenant_id=user.tenant_id)
