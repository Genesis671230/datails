"""LD-28 acceptance: Idempotency-Key on expensive POSTs.

Replay of the same key returns the original response without re-executing
the connector run; the same key with a different payload returns 409.
"""

import uuid

from sqlalchemy import func, select

from app.db.models import ConnectorRun
from app.tests.helpers import bootstrap_tenant

LOOKUP = "/api/v1/connectors/crystal/wallet-lookup"
BODY = {"address": "bc1qidem", "chain": "bitcoin", "mode": "risk_check"}


async def _register_crystal(client, tenant) -> dict:
    response = await client.post(
        "/api/v1/connectors",
        json={"name": "Crystal", "connector_type": "crystal",
              "credential_owner": "datails_shared"},
        headers=tenant.headers,
    )
    assert response.status_code == 201
    return response.json()


def _headers(tenant, key: str) -> dict:
    return {**tenant.headers, "Idempotency-Key": key}


async def test_missing_idempotency_key_rejected(client) -> None:
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant)
    response = await client.post(LOOKUP, json=BODY, headers=tenant.headers)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"


async def test_replay_returns_original_without_second_run(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    connector = await _register_crystal(client, tenant)
    key = f"idem-{uuid.uuid4().hex}"

    first = await client.post(LOOKUP, json=BODY, headers=_headers(tenant, key))
    assert first.status_code == 200
    second = await client.post(LOOKUP, json=BODY, headers=_headers(tenant, key))
    assert second.status_code == 200
    assert second.headers.get("x-idempotent-replay") == "true"
    assert second.json() == first.json(), "replay must return the original response"

    run_count = (
        await app_session.execute(
            select(func.count(ConnectorRun.id)).where(
                ConnectorRun.connector_id == uuid.UUID(connector["id"])
            )
        )
    ).scalar_one()
    assert run_count == 1, "replay must not execute a second connector run"


async def test_same_key_different_payload_conflicts(client) -> None:
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant)
    key = f"idem-{uuid.uuid4().hex}"

    first = await client.post(LOOKUP, json=BODY, headers=_headers(tenant, key))
    assert first.status_code == 200
    conflicting = await client.post(
        LOOKUP, json={**BODY, "address": "bc1qother"}, headers=_headers(tenant, key)
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["error"]["code"] == "idempotency_key_conflict"


async def test_keys_are_tenant_scoped(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    await _register_crystal(client, tenant_a)
    await _register_crystal(client, tenant_b)
    key = f"idem-{uuid.uuid4().hex}"

    first = await client.post(LOOKUP, json=BODY, headers=_headers(tenant_a, key))
    assert first.status_code == 200
    other_tenant = await client.post(LOOKUP, json=BODY, headers=_headers(tenant_b, key))
    assert other_tenant.status_code == 200
    assert other_tenant.headers.get("x-idempotent-replay") is None, (
        "same key under another tenant is a fresh request"
    )


async def test_failed_runs_are_not_recorded_for_replay(client) -> None:
    """A 4xx/5xx outcome must stay retryable under the same key."""
    tenant = await bootstrap_tenant(client)
    # No connector registered → 404 on first call.
    key = f"idem-{uuid.uuid4().hex}"
    first = await client.post(LOOKUP, json=BODY, headers=_headers(tenant, key))
    assert first.status_code == 404

    await _register_crystal(client, tenant)
    retry = await client.post(LOOKUP, json=BODY, headers=_headers(tenant, key))
    assert retry.status_code == 200, "after fixing the cause, the same key must work"


async def test_unprotected_routes_need_no_key(client) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        "/api/v1/cases",
        json={"title": "no key needed", "case_type": "criminal_investigation"},
        headers=tenant.headers,
    )
    assert response.status_code == 201
