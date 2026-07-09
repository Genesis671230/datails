"""Connector layer tests (Slice 1).

Covers: registry routes, LD-18.2 test-call persists nothing, the LD-4
pipeline on replay fixtures (snapshot → hash → data_ledger, one transaction),
LD-14 label provenance, LD-11 derived daily limits, LD-22 shared-key budget,
failure semantics, and tenant isolation.
"""

import uuid

from sqlalchemy import func, select

from app.db.models import (
    Connector,
    ConnectorRun,
    DataLedgerEntry,
    WalletLabel,
)
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers

LOOKUP = "/api/v1/connectors/crystal/wallet-lookup"
LOOKUP_ATTACH = "/api/v1/connectors/crystal/wallet-lookup-and-attach"


async def _register_crystal(client, tenant, **overrides) -> dict:
    payload = {
        "name": "Crystal (shared pilot key)",
        "connector_type": "crystal",
        "credential_owner": "datails_shared",
        **overrides,
    }
    response = await client.post("/api/v1/connectors", json=payload, headers=tenant.headers)
    assert response.status_code == 201, response.text
    return response.json()


# --- registry ----------------------------------------------------------------


async def test_register_and_list_connectors(client) -> None:
    tenant = await bootstrap_tenant(client)
    created = await _register_crystal(client, tenant)
    listed = (await client.get("/api/v1/connectors", headers=tenant.headers)).json()
    assert [c["id"] for c in listed] == [created["id"]]
    assert listed[0]["credential_owner"] == "datails_shared"


async def test_reserved_types_not_registrable(client) -> None:
    tenant = await bootstrap_tenant(client)
    for connector_type in ("mcp_server", "generic_api"):
        response = await client.post(
            "/api/v1/connectors",
            json={"name": "x", "connector_type": connector_type},
            headers=tenant.headers,
        )
        assert response.status_code == 422, connector_type


async def test_connector_test_call_persists_nothing(client, app_session) -> None:
    """LD-18.2: the Phase 4-style test call verifies configuration only."""
    tenant = await bootstrap_tenant(client)
    connector = await _register_crystal(client, tenant, secret_ref="MISSING_TEST_SECRET")

    response = await client.post(
        f"/api/v1/connectors/{connector['id']}/test", headers=tenant.headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["secret_resolved"] is False
    assert body["transport"] == "replay"

    runs = (
        await app_session.execute(
            select(func.count(ConnectorRun.id)).where(
                ConnectorRun.connector_id == uuid.UUID(connector["id"])
            )
        )
    ).scalar_one()
    ledger = (
        await app_session.execute(
            select(func.count(DataLedgerEntry.id)).where(
                DataLedgerEntry.connector_id == uuid.UUID(connector["id"])
            )
        )
    ).scalar_one()
    assert (runs, ledger) == (0, 0), "test call must persist nothing (LD-18.2)"


# --- LD-4 pipeline on replay fixtures ----------------------------------------


async def test_wallet_lookup_round_trip(client, app_session) -> None:
    """Replay lookup: snapshot in blob, hash in data_ledger, run completed,
    visible via GET /api/v1/ledger/data."""
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant)

    response = await client.post(
        LOOKUP,
        json={"address": "bc1qsomeaddress", "chain": "bitcoin", "mode": "risk_check"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["payload_hash"]) == 64
    assert body["storage_ref"].startswith("local://snapshots/")
    assert body["risk_color"] == "green"
    assert body["labels"][0]["label"] == "Binance"

    ledger = (
        await client.get("/api/v1/ledger/data", headers=tenant.headers)
    ).json()
    assert len(ledger) == 1
    assert ledger[0]["payload_hash"] == body["payload_hash"]
    assert ledger[0]["storage_ref"] == body["storage_ref"]

    run = (
        await app_session.execute(
            select(ConnectorRun).where(ConnectorRun.id == uuid.UUID(body["connector_run_id"]))
        )
    ).scalar_one()
    assert run.status.value == "completed"
    assert run.response_ref == body["storage_ref"]


async def test_lookup_and_attach_writes_wallet_labels_with_provenance(
    client, app_session
) -> None:
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant)
    case = await create_case(client, tenant)

    response = await client.post(
        LOOKUP_ATTACH,
        json={
            "case_id": case["id"],
            "address": "bc1qexchangedeposit",
            "chain": "bitcoin",
            "mode": "risk_check",
            "role_in_case": "exchange_deposit",
        },
        headers=idem_headers(tenant),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["wallet_id"] is not None

    labels = (
        (
            await app_session.execute(
                select(WalletLabel).where(
                    WalletLabel.wallet_id == uuid.UUID(body["wallet_id"])
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(labels) == 1
    label = labels[0]
    assert label.label == "Binance"
    assert label.source_type.value == "connector"
    assert label.data_ledger_id == body["data_ledger_id"], "LD-14 provenance link"

    detail = (await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)).json()
    assert body["wallet_id"] in [w["id"] for w in detail["wallets"]]
    ledger = (await client.get("/api/v1/ledger/data", headers=tenant.headers)).json()
    assert ledger[0]["case_id"] == case["id"]


async def test_full_investigation_mode_returns_transfers(client) -> None:
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant)

    response = await client.post(
        LOOKUP,
        json={"address": "bc1qsuspect", "chain": "bitcoin", "mode": "full_investigation"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 200
    assert len(response.json()["transfers"]) == 2


# --- limits (LD-11, LD-22) ----------------------------------------------------


async def test_per_connector_daily_limit_enforced(client) -> None:
    tenant = await bootstrap_tenant(client)
    await _register_crystal(client, tenant, daily_call_limit=1)
    body = {"address": "bc1qx", "chain": "bitcoin", "mode": "risk_check"}

    first = await client.post(LOOKUP, json=body, headers=idem_headers(tenant))
    assert first.status_code == 200
    second = await client.post(LOOKUP, json=body, headers=idem_headers(tenant))
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "limit_exceeded"


async def test_shared_key_budget_enforced_across_tenants(client, monkeypatch) -> None:
    """LD-22: one cohort member must not starve the others — the budget is
    global across tenants for the shared key."""
    from app.core.config import get_settings

    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    await _register_crystal(client, tenant_a)
    await _register_crystal(client, tenant_b)
    body = {"address": "bc1qy", "chain": "bitcoin", "mode": "risk_check"}

    used = (await client.post(LOOKUP, json=body, headers=idem_headers(tenant_a))).status_code
    assert used == 200
    monkeypatch.setattr(get_settings(), "shared_key_daily_budget", 1)
    blocked = await client.post(LOOKUP, json=body, headers=idem_headers(tenant_b))
    assert blocked.status_code == 429
    assert "shared key" in blocked.json()["error"]["message"]


# --- failure semantics (LD-4) ---------------------------------------------------


async def test_failed_external_call_leaves_no_ledger_entry(client, app_session) -> None:
    """Mock connector simulated failure: run failed, no blob ref, no ledger."""
    from app.db.models.enums import ConnectorType
    from app.schemas.connectors import WalletLookupRequest
    from app.services.connectors.wallet_lookup import wallet_lookup
    from app.tests.factories import create_tenant, create_user, create_workspace

    tenant = await create_tenant(app_session)
    user = await create_user(app_session, tenant)
    workspace = await create_workspace(app_session, tenant)
    connector = Connector(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        name="mock",
        connector_type=ConnectorType.GENERIC_API,
    )
    app_session.add(connector)
    await app_session.commit()

    import pytest

    from app.core.errors import UpstreamError

    request = WalletLookupRequest.model_construct(
        address="x", chain="y", mode="risk_check"
    )
    # Drive the failure through the mock's simulate_failure hook.
    from app.services.connectors import wallet_lookup as wl_module

    original = wl_module.execute_connector_operation

    async def with_failure(session, conn, *, operation, params, **kwargs):
        return await original(
            session, conn, operation=operation,
            params={**params, "simulate_failure": True}, **kwargs,
        )

    monkey_target = wl_module
    monkey_target.execute_connector_operation = with_failure
    try:
        with pytest.raises(UpstreamError):
            await wallet_lookup(
                app_session, tenant.id, user.id, ConnectorType.GENERIC_API, request
            )
    finally:
        monkey_target.execute_connector_operation = original

    run = (
        await app_session.execute(
            select(ConnectorRun).where(ConnectorRun.connector_id == connector.id)
        )
    ).scalar_one()
    assert run.status.value == "failed"
    assert "simulated failure" in run.error_message
    assert run.response_ref is None

    ledger_count = (
        await app_session.execute(
            select(func.count(DataLedgerEntry.id)).where(
                DataLedgerEntry.connector_id == connector.id
            )
        )
    ).scalar_one()
    assert ledger_count == 0, "LD-4: no ledger entry without a payload"


# --- tenant isolation -----------------------------------------------------------


async def test_connectors_and_lookups_are_tenant_isolated(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    connector_a = await _register_crystal(client, tenant_a)

    listed_b = (await client.get("/api/v1/connectors", headers=tenant_b.headers)).json()
    assert listed_b == []

    test_cross = await client.post(
        f"/api/v1/connectors/{connector_a['id']}/test", headers=tenant_b.headers
    )
    assert test_cross.status_code == 404

    lookup_b = await client.post(
        LOOKUP,
        json={"address": "bc1qz", "chain": "bitcoin", "mode": "risk_check"},
        headers=idem_headers(tenant_b),
    )
    assert lookup_b.status_code == 404, "tenant B has no crystal connector registered"


async def test_lookup_without_registered_connector_404(client) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        LOOKUP,
        json={"address": "bc1q", "chain": "bitcoin", "mode": "risk_check"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 404
