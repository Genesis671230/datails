"""Health endpoint.

The only route exempt from JWT validation (LD-1). Reports app liveness plus
a non-fatal database connectivity indicator — a degraded DB shows in the
payload rather than failing the probe, so orchestrator restarts are reserved
for real process death.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_sessionmaker

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    database = "ok"
    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database = "unavailable"
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": database,
    }
