"""Entra External ID JWT validation middleware (LD-1).

Every request except `/api/v1/health` must carry a valid Entra-issued JWT
(signature, issuer, audience, expiry). The middleware only validates and
attaches claims — it never touches the database and never provisions
tenants (provisioning happens exclusively in POST /api/v1/workspaces/bootstrap).

Tenant context is derived downstream from the validated `oid` claim only —
never from client-supplied bodies, params, or headers.

A local-development bypass exists behind AUTH_DEV_MODE=true; configuration
hard-fails if that flag is set outside ENVIRONMENT=local (see core/config.py).
"""

import time
from dataclasses import dataclass

import httpx
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.logging import get_logger, log_fields, request_id_var

logger = get_logger(__name__)

EXEMPT_PATHS = frozenset({"/api/v1/health"})
JWKS_CACHE_TTL_SECONDS = 3600
ALLOWED_ALGORITHMS = ["RS256"]


@dataclass(frozen=True)
class AuthClaims:
    """Validated identity claims attached to the request."""

    oid: str
    email: str | None
    name: str | None


class JwksCache:
    """Fetches and caches the Entra JWKS document.

    Tests seed this cache directly (`seed`) so token validation exercises the
    real code path without a network dependency.
    """

    def __init__(self) -> None:
        self._keys: dict[str, dict] = {}
        self._fetched_at: float = 0.0
        self._seeded = False

    def seed(self, jwks: dict) -> None:
        self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
        self._seeded = True

    def clear(self) -> None:
        self._keys = {}
        self._fetched_at = 0.0
        self._seeded = False

    async def get_key(self, kid: str) -> dict | None:
        if not self._seeded and (
            not self._keys or time.monotonic() - self._fetched_at > JWKS_CACHE_TTL_SECONDS
        ):
            await self._fetch()
        return self._keys.get(kid)

    async def _fetch(self) -> None:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(settings.jwks_url)
            response.raise_for_status()
            self.seed(response.json())
            self._seeded = False
            self._fetched_at = time.monotonic()


jwks_cache = JwksCache()


def _unauthorized(message: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "error": {
                "code": "unauthenticated",
                "message": message,
                "request_id": request_id_var.get() or "",
            }
        },
    )


async def _validate_token(token: str) -> AuthClaims:
    """Validate signature, issuer, audience, and expiry; return claims.

    Raises jwt.InvalidTokenError (or subclasses) on any failure.
    """
    settings = get_settings()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not kid:
        raise jwt.InvalidTokenError("token header missing kid")

    jwk = await jwks_cache.get_key(kid)
    if jwk is None:
        raise jwt.InvalidTokenError("signing key not found")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    payload = jwt.decode(
        token,
        key=public_key,
        algorithms=ALLOWED_ALGORITHMS,
        audience=settings.entra_audience,
        issuer=settings.expected_issuer,
        options={"require": ["exp", "iss", "aud"]},
    )
    oid = payload.get("oid")
    if not oid:
        raise jwt.InvalidTokenError("token missing oid claim")
    return AuthClaims(
        oid=oid,
        email=payload.get("email") or payload.get("preferred_username"),
        name=payload.get("name"),
    )


class EntraJwtMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        settings = get_settings()
        if settings.auth_dev_mode:
            # Local development only; config hard-fails outside ENVIRONMENT=local.
            request.state.auth_claims = AuthClaims(
                oid=settings.dev_user_oid, email=settings.dev_user_email, name="Dev User"
            )
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return _unauthorized("Missing bearer token.")

        try:
            claims = await _validate_token(authorization.removeprefix("Bearer ").strip())
        except jwt.InvalidTokenError as exc:
            logger.info(
                "token rejected: %s",
                exc,
                extra=log_fields(module="auth", action="validate_token", status="rejected"),
            )
            return _unauthorized("Invalid token.")

        request.state.auth_claims = claims
        return await call_next(request)
