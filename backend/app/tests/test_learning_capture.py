"""LD-30 tests: learning capture is consent-gated.

learning_events appear ONLY when tenants.learning_capture_enabled is true;
capturing without the flag is a defect.
"""

import uuid

from sqlalchemy import select, update

from app.db.models import LearningEvent, Tenant
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers


async def _events_for(app_session, tenant_id: str) -> list[LearningEvent]:
    return list(
        (
            await app_session.execute(
                select(LearningEvent).where(
                    LearningEvent.tenant_id == uuid.UUID(tenant_id)
                )
            )
        ).scalars()
    )


async def _enable_capture(owner_session, tenant_id: str) -> None:
    await owner_session.execute(
        update(Tenant)
        .where(Tenant.id == uuid.UUID(tenant_id))
        .values(learning_capture_enabled=True)
    )
    await owner_session.commit()


async def _draft_and_approve(client, tenant) -> str:
    case = await create_case(client, tenant)
    draft = await client.post(
        "/api/v1/reports/draft",
        json={"case_id": case["id"], "report_type": "investigator_summary",
              "title": "Summary"},
        headers=idem_headers(tenant),
    )
    report_id = draft.json()["report"]["id"]
    approved = await client.post(
        f"/api/v1/reports/{report_id}/approve", headers=tenant.headers
    )
    assert approved.status_code == 200
    return report_id


async def test_no_capture_without_consent(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)  # learning_capture_enabled defaults false
    await _draft_and_approve(client, tenant)
    assert await _events_for(app_session, tenant.tenant_id) == [], (
        "capturing without the consent flag is a defect (LD-30)"
    )


async def test_capture_with_consent(client, app_session, owner_session) -> None:
    tenant = await bootstrap_tenant(client)
    await _enable_capture(owner_session, tenant.tenant_id)
    report_id = await _draft_and_approve(client, tenant)

    events = await _events_for(app_session, tenant.tenant_id)
    assert len(events) == 1
    event = events[0]
    assert event.event_type.value == "draft_approved"
    assert event.subject_type == "report"
    assert event.subject_id == report_id
    assert "content" not in (event.payload_json or {}), "no raw case content in payloads"


async def test_ingest_route_captures_with_consent(client, app_session, owner_session) -> None:
    tenant = await bootstrap_tenant(client)
    await _enable_capture(owner_session, tenant.tenant_id)
    case = await create_case(client, tenant)

    response = await client.post(
        "/api/v1/learning-events",
        json={"event_type": "recommendation_rejected", "subject_type": "assistant_answer",
              "subject_id": "some-answer-id", "case_id": case["id"],
              "payload": {"reason_category": "wrong_direction"}},
        headers=tenant.headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["captured"] is True
    events = await _events_for(app_session, tenant.tenant_id)
    assert any(e.event_type.value == "recommendation_rejected" for e in events)


async def test_ingest_route_noop_without_consent(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        "/api/v1/learning-events",
        json={"event_type": "report_edited", "subject_type": "report", "subject_id": "x"},
        headers=tenant.headers,
    )
    assert response.status_code == 201
    assert response.json() == {"captured": False, "event_id": None}
    assert await _events_for(app_session, tenant.tenant_id) == []


async def test_ingest_route_rejects_unknown_event_type(client) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        "/api/v1/learning-events",
        json={"event_type": "telepathy", "subject_type": "report", "subject_id": "x"},
        headers=tenant.headers,
    )
    assert response.status_code == 422, "05 §9 vocabulary is the contract"


async def test_ingest_route_rejects_foreign_case(client, owner_session) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    await _enable_capture(owner_session, tenant_b.tenant_id)
    case_a = await create_case(client, tenant_a)
    response = await client.post(
        "/api/v1/learning-events",
        json={"event_type": "report_edited", "subject_type": "report",
              "subject_id": "x", "case_id": case_a["id"]},
        headers=tenant_b.headers,
    )
    assert response.status_code == 404


async def test_learning_events_route_in_openapi(app) -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/learning-events" in paths, "frontend contract per LD-26"


async def test_learning_events_are_insert_only(client, app_session, owner_session) -> None:
    """learning_events sits under the same LD-3 enforcement as the ledgers."""
    import pytest
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError, ProgrammingError

    tenant = await bootstrap_tenant(client)
    await _enable_capture(owner_session, tenant.tenant_id)
    await _draft_and_approve(client, tenant)
    event_id = (await _events_for(app_session, tenant.tenant_id))[0].id

    with pytest.raises(ProgrammingError, match="permission denied"):
        await app_session.execute(
            text("DELETE FROM learning_events WHERE id = :id"), {"id": event_id}
        )
    await app_session.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        await owner_session.execute(
            text("UPDATE learning_events SET subject_type = 'x' WHERE id = :id"),
            {"id": event_id},
        )
    await owner_session.rollback()
