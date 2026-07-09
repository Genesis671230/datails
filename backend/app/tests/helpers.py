"""Shared test helpers for authenticated API flows."""

import uuid
from dataclasses import dataclass

from httpx import AsyncClient

from app.tests.auth_utils import mint_token


@dataclass(frozen=True)
class TenantSession:
    """A bootstrapped tenant plus the auth header to act as its owner."""

    tenant_id: str
    workspace_id: str
    user_id: str
    headers: dict[str, str]


async def bootstrap_tenant(client: AsyncClient, name: str | None = None) -> TenantSession:
    token = mint_token(str(uuid.uuid4()))
    response = await client.post(
        "/api/v1/workspaces/bootstrap",
        json={"tenant_name": name or f"Tenant {uuid.uuid4().hex[:6]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return TenantSession(
        tenant_id=body["tenant"]["id"],
        workspace_id=body["workspace"]["id"],
        user_id=body["user"]["id"],
        headers={"Authorization": f"Bearer {token}"},
    )


def idem_headers(session: TenantSession) -> dict[str, str]:
    """Auth headers plus a fresh Idempotency-Key (LD-28 routes)."""
    return {**session.headers, "Idempotency-Key": f"test-{uuid.uuid4().hex}"}


async def create_case(client: AsyncClient, session: TenantSession, **overrides) -> dict:
    payload = {
        "title": "Investment scam — victim intake",
        "case_type": "criminal_investigation",
        **overrides,
    }
    response = await client.post("/api/v1/cases", json=payload, headers=session.headers)
    assert response.status_code == 201, response.text
    return response.json()
