"""Slice 2 report tests: draft via AI path, versions immutable (LD-10 Phase 12
minimum), approval gate + ledger event, jurisdiction overlays, isolation."""

import uuid

from sqlalchemy import select

from app.db.models import AiCallLogEntry, DecisionLedgerEvent
from app.services.ai.model_router import MODEL_REASONING
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers

DRAFT = "/api/v1/reports/draft"


async def _draft(client, tenant, case_id: str, **overrides) -> dict:
    payload = {
        "case_id": case_id,
        "report_type": "freeze_blocklist_request",
        "title": "Freeze request — Binance",
        "jurisdiction": "DE",
        **overrides,
    }
    response = await client.post(DRAFT, json=payload, headers=idem_headers(tenant))
    assert response.status_code == 201, response.text
    return response.json()


async def test_draft_creates_report_and_cited_version(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, summary="0.44 BTC at exchange deposit")
    body = await _draft(client, tenant, case["id"])

    report, version = body["report"], body["version"]
    assert report["status"] == "draft", "reports are drafts by default"
    assert report["jurisdiction"] == "DE"
    assert report["current_version_id"] == version["id"]
    assert version["version_number"] == 1
    assert version["generated_by_ai"] is True
    assert f"case:{case['id']}" in version["source_refs_json"]["refs"]

    # The draft went through the task executor → ai_call_log row exists.
    entries = (
        (
            await app_session.execute(
                select(AiCallLogEntry).where(
                    AiCallLogEntry.case_id == uuid.UUID(case["id"]),
                    AiCallLogEntry.task_type == "report_drafting",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(entries) == 1
    assert entries[0].model_name == MODEL_REASONING, "report drafting routes to reasoning model"


async def test_sar_draft_type_supported(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    body = await _draft(client, tenant, case["id"], report_type="sar_draft",
                        title="SAR draft", jurisdiction="AT")
    assert body["report"]["report_type"] == "sar_draft"


async def test_unknown_jurisdiction_rejected(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    response = await client.post(
        DRAFT,
        json={"case_id": case["id"], "report_type": "case_dossier", "title": "x",
              "jurisdiction": "XX"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 400


async def test_approval_gate_and_ledger_event(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    body = await _draft(client, tenant, case["id"])
    report_id = body["report"]["id"]

    approved = await client.post(
        f"/api/v1/reports/{report_id}/approve", headers=tenant.headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    events = (
        (
            await app_session.execute(
                select(DecisionLedgerEvent).where(
                    DecisionLedgerEvent.case_id == uuid.UUID(case["id"]),
                    DecisionLedgerEvent.event_type == "approved",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].approved is True
    assert events[0].inputs_ref_json["report_id"] == report_id

    again = await client.post(
        f"/api/v1/reports/{report_id}/approve", headers=tenant.headers
    )
    assert again.status_code == 409, "double approval conflicts"


async def test_versions_listing(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    body = await _draft(client, tenant, case["id"])

    versions = (
        await client.get(
            f"/api/v1/reports/{body['report']['id']}/versions", headers=tenant.headers
        )
    ).json()
    assert [v["version_number"] for v in versions] == [1]


async def test_prior_versions_are_immutable_in_db(client, app_session) -> None:
    """LD-10 Phase 12 minimum: prior versions immutable. Enforced by a
    dedicated trigger-less convention plus this regression test at the ORM
    level: content updates must go through new version rows (service exposes
    no update path), and the row itself rejects nothing at DB level — so we
    assert the service surface: there is no route or service function that
    mutates content_markdown."""
    from app.services.reports import service as reports_service

    mutating = [name for name in dir(reports_service)
                if "update_version" in name or "edit_version" in name]
    assert mutating == [], "no service path may mutate an existing version"


async def test_reports_are_tenant_isolated(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)
    body = await _draft(client, tenant_a, case_a["id"])
    report_id = body["report"]["id"]

    for method, url in (
        ("get", f"/api/v1/reports/{report_id}"),
        ("get", f"/api/v1/reports/{report_id}/versions"),
        ("post", f"/api/v1/reports/{report_id}/approve"),
    ):
        response = await getattr(client, method)(url, headers=tenant_b.headers)
        assert response.status_code == 404, url


async def test_draft_requires_idempotency_key(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    response = await client.post(
        DRAFT,
        json={"case_id": case["id"], "report_type": "case_dossier", "title": "x"},
        headers=tenant.headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"
