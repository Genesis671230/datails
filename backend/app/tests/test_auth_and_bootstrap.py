"""LD-1 acceptance tests.

Valid Entra-style JWT → tenant context; missing/invalid → 401; provisioning
only via bootstrap; tenant isolation between two authenticated users.
Tokens are real RS256 JWTs validated by the real middleware code path.
"""

import uuid

from app.tests.auth_utils import TEST_AUDIENCE, TEST_AUTHORITY, mint_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- rejection paths -------------------------------------------------------


async def test_health_needs_no_token(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_missing_token_rejected(client) -> None:
    response = await client.post("/api/v1/workspaces/bootstrap", json={})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_garbage_token_rejected(client) -> None:
    response = await client.post(
        "/api/v1/workspaces/bootstrap", json={}, headers=_auth("not-a-jwt")
    )
    assert response.status_code == 401


async def test_expired_token_rejected(client) -> None:
    token = mint_token(expires_in=-60)
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 401


async def test_wrong_audience_rejected(client) -> None:
    token = mint_token(audience="api://someone-else")
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 401


async def test_wrong_issuer_rejected(client) -> None:
    token = mint_token(issuer="https://evil.example/v2.0")
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 401


async def test_unknown_signing_key_rejected(client) -> None:
    token = mint_token(kid="unknown-kid")
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 401


async def test_token_without_oid_rejected(client) -> None:
    token = mint_token(drop_claims=("oid",))
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 401


# --- bootstrap and context -------------------------------------------------


async def test_bootstrap_creates_tenant_user_workspace(client) -> None:
    oid = str(uuid.uuid4())
    token = mint_token(oid, email="albert@example.test", name="Albert Q")

    response = await client.post(
        "/api/v1/workspaces/bootstrap", json={"tenant_name": "AQ Forensics"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant"]["name"] == "AQ Forensics"
    assert body["tenant"]["region"] == "westeurope"
    assert body["tenant"]["learning_capture_enabled"] is False, "LD-30 default"
    assert body["user"]["role"] == "owner"
    assert body["workspace"]["is_default"] is True
    assert body["onboarding_status"] == "started"


async def test_bootstrap_is_idempotent_for_known_oid(client) -> None:
    oid = str(uuid.uuid4())
    token = mint_token(oid)

    first = await client.post("/api/v1/workspaces/bootstrap", json={}, headers=_auth(token))
    second = await client.post("/api/v1/workspaces/bootstrap", json={}, headers=_auth(token))
    assert first.status_code == second.status_code == 200
    assert first.json()["tenant"]["id"] == second.json()["tenant"]["id"]
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_me_returns_bootstrapped_context(client) -> None:
    oid = str(uuid.uuid4())
    token = mint_token(oid)
    created = await client.post(
        "/api/v1/workspaces/bootstrap", json={}, headers=_auth(token)
    )

    me = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["tenant"]["id"] == created.json()["tenant"]["id"]


async def test_me_before_bootstrap_is_not_found(client) -> None:
    token = mint_token(str(uuid.uuid4()))
    response = await client.get("/api/v1/workspaces/me", headers=_auth(token))
    assert response.status_code == 404


# --- tenant isolation (LD-10) ----------------------------------------------


async def test_two_identities_get_isolated_tenants(client) -> None:
    token_a = mint_token(str(uuid.uuid4()), email="a@example.test")
    token_b = mint_token(str(uuid.uuid4()), email="b@example.test")

    a = (await client.post("/api/v1/workspaces/bootstrap", json={}, headers=_auth(token_a))).json()
    b = (await client.post("/api/v1/workspaces/bootstrap", json={}, headers=_auth(token_b))).json()

    assert a["tenant"]["id"] != b["tenant"]["id"]
    assert a["workspace"]["id"] != b["workspace"]["id"]

    me_a = (await client.get("/api/v1/workspaces/me", headers=_auth(token_a))).json()
    me_b = (await client.get("/api/v1/workspaces/me", headers=_auth(token_b))).json()
    assert me_a["tenant"]["id"] == a["tenant"]["id"]
    assert me_b["tenant"]["id"] == b["tenant"]["id"]


# --- configuration sanity ---------------------------------------------------


def test_test_configuration_matches_settings() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.entra_audience == TEST_AUDIENCE
    assert settings.expected_issuer == TEST_AUTHORITY
