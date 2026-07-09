"""Request-context middleware.

Assigns every request a request_id and binds it (plus, once authentication
resolves, tenant/actor identifiers) into logging contextvars so all log lines
emitted while handling the request are correlated (Block J).
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import (
    actor_id_var,
    get_logger,
    log_fields,
    request_id_var,
    tenant_id_var,
    workspace_id_var,
)

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        tenant_id_var.set(None)
        workspace_id_var.set(None)
        actor_id_var.set(None)

        started = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra=log_fields(
                module="http",
                action=f"{request.method} {request.url.path}",
                status=str(response.status_code),
            ),
        )
        return response
