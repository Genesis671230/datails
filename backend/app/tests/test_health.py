"""Slice 0 scaffold tests: health route, request correlation, config guard.

All HTTP tests use the shared async client (one event loop for app, engine,
and tests) — a sync TestClient would run the app in a separate loop and
poison the shared connection pool.
"""

import pytest

from app.core.config import Settings


async def test_health_returns_ok(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "datails-backend"
    assert body["database"] == "ok"


async def test_health_response_carries_request_id_header(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")


async def test_unknown_route_requires_auth_first(client) -> None:
    # Auth middleware runs before routing: everything except /api/v1/health
    # needs a token (LD-1), even unknown paths.
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 401


def test_auth_dev_mode_rejected_outside_local() -> None:
    with pytest.raises(ValueError, match="AUTH_DEV_MODE"):
        Settings(environment="prod", auth_dev_mode=True)


def test_auth_dev_mode_allowed_in_local() -> None:
    settings = Settings(environment="local", auth_dev_mode=True)
    assert settings.auth_dev_mode is True
