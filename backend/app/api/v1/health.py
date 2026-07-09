"""Health endpoint.

The only route exempt from JWT validation (LD-1). Reports app liveness only;
deeper dependency checks belong to observability, not the liveness probe.
"""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }
