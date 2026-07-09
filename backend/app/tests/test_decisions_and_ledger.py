"""LD-9 and LD-8 tests: decision writes emit ledger events in the same
transaction; ledger read endpoints are tenant-scoped and newest first."""

import uuid

import pytest
from sqlalchemy import select

from app.core.errors import NotFoundError
from app.db.models import Decision, DecisionLedgerEvent
from app.schemas.decisions import DecisionCreate
from app.services.decisions import service as decisions_service
from app.tests.helpers import bootstrap_tenant, create_case


async def _post_decision(client, tenant, case_id: str, **overrides) -> dict:
    payload = {
        "case_id": case_id,
        "decision_type": "open_case",
        "description": "Open the investigation",
        **overrides,
    }
    response = await client.post("/api/v1/decisions", json=payload, headers=tenant.headers)
    assert response.status_code == 201, response.text
    return response.json()


async def test_decision_write_emits_ledger_event(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    decision = await _post_decision(client, tenant, case["id"])

    events = (
        (
            await app_session.execute(
                select(DecisionLedgerEvent).where(
                    DecisionLedgerEvent.decision_id == uuid.UUID(decision["id"])
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_type.value == "created"
    assert event.actor_type == "user"
    assert str(event.case_id) == case["id"]


async def test_decision_and_event_are_atomic(client, app_session, monkeypatch) -> None:
    """LD-9: if the ledger event cannot be written, the decision must not
    persist either."""
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)

    async def failing_writer(*args, **kwargs):
        raise RuntimeError("simulated ledger failure")

    monkeypatch.setattr(decisions_service, "write_decision_event", failing_writer)
    with pytest.raises(RuntimeError, match="simulated ledger failure"):
        await decisions_service.create_decision(
            app_session,
            uuid.UUID(tenant.tenant_id),
            uuid.UUID(tenant.user_id),
            DecisionCreate(
                case_id=uuid.UUID(case["id"]),
                decision_type="open_case",
                description="Must roll back",
            ),
        )
    await app_session.rollback()

    decisions = (
        (
            await app_session.execute(
                select(Decision).where(Decision.case_id == uuid.UUID(case["id"]))
            )
        )
        .scalars()
        .all()
    )
    assert decisions == [], "decision must roll back with its ledger event"


async def test_decision_appears_in_case_detail(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    await _post_decision(client, tenant, case["id"])

    detail = (await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)).json()
    assert len(detail["decisions"]) == 1
    assert detail["decisions"][0]["decision_type"] == "open_case"


async def test_decision_for_foreign_case_404(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)

    response = await client.post(
        "/api/v1/decisions",
        json={"case_id": case_a["id"], "decision_type": "open_case", "description": "x"},
        headers=tenant_b.headers,
    )
    assert response.status_code == 404


async def test_decision_ledger_read_newest_first_and_filtered(client) -> None:
    tenant = await bootstrap_tenant(client)
    case_one = await create_case(client, tenant, title="One")
    case_two = await create_case(client, tenant, title="Two")
    await _post_decision(client, tenant, case_one["id"], description="first")
    await _post_decision(client, tenant, case_two["id"], description="second")

    all_events = (
        await client.get("/api/v1/ledger/decision", headers=tenant.headers)
    ).json()
    assert len(all_events) == 2
    assert all_events[0]["id"] > all_events[1]["id"], "newest first"

    filtered = (
        await client.get(
            f"/api/v1/ledger/decision?case_id={case_one['id']}", headers=tenant.headers
        )
    ).json()
    assert len(filtered) == 1
    assert filtered[0]["case_id"] == case_one["id"]


async def test_ledger_reads_are_tenant_isolated(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)
    await _post_decision(client, tenant_a, case_a["id"])

    events_b = (
        await client.get("/api/v1/ledger/decision", headers=tenant_b.headers)
    ).json()
    assert events_b == []

    data_b = (await client.get("/api/v1/ledger/data", headers=tenant_b.headers)).json()
    assert data_b == []


async def test_create_decision_service_missing_case(app_session) -> None:
    from app.tests.factories import create_tenant, create_user

    tenant = await create_tenant(app_session)
    user = await create_user(app_session, tenant)
    with pytest.raises(NotFoundError):
        await decisions_service.create_decision(
            app_session,
            tenant.id,
            user.id,
            DecisionCreate(
                case_id=uuid.uuid4(), decision_type="open_case", description="x"
            ),
        )
