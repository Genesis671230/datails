"""Datails backend application entrypoint.

Wires the FastAPI app: configuration, structured logging, error handling,
request-context middleware, and versioned routers. Route modules stay thin;
all business logic lives in services.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import cases, decisions, findings, health, ledger, workspaces
from app.core.auth import EntraJwtMiddleware
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger, log_fields
from app.core.request_context import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "starting %s (environment=%s)",
        settings.app_name,
        settings.environment,
        extra=log_fields(module="main", action="startup", status="ok"),
    )
    yield
    logger.info(
        "shutting down",
        extra=log_fields(module="main", action="shutdown", status="ok"),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Datails Backend",
        version="0.1.0",
        description=(
            "Case-centric Operational AI Workspace for digital asset "
            "investigations and compliance."
        ),
        lifespan=lifespan,
    )

    # Middleware order (outermost first at request time): request context
    # assigns request_id before auth runs, so 401s are correlated too.
    app.add_middleware(EntraJwtMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(workspaces.router, prefix="/api/v1", tags=["workspaces"])
    app.include_router(cases.router, prefix="/api/v1", tags=["cases"])
    app.include_router(findings.router, prefix="/api/v1", tags=["findings"])
    app.include_router(decisions.router, prefix="/api/v1", tags=["decisions"])
    app.include_router(ledger.router, prefix="/api/v1", tags=["ledger"])
    return app


app = create_app()
