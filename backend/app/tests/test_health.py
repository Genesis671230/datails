"""Slice 0 scaffold tests: health route, error envelope, config guard."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "datails-backend"


def test_health_response_carries_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404


def test_auth_dev_mode_rejected_outside_local() -> None:
    with pytest.raises(ValueError, match="AUTH_DEV_MODE"):
        Settings(environment="prod", auth_dev_mode=True)


def test_auth_dev_mode_allowed_in_local() -> None:
    settings = Settings(environment="local", auth_dev_mode=True)
    assert settings.auth_dev_mode is True
