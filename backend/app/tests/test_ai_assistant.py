"""Slice 2 tests: assistant endpoint (LD-20) + task executor logging.

Every AI call — success or failure — must produce an ai_call_log row with
model, hashes, latency, and status (01 §9; hard-stop check).
"""

import uuid

from sqlalchemy import select

from app.db.models import AiCallLogEntry
from app.services.ai.model_router import MODEL_FORMATTING, MODEL_REASONING
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers

ASSISTANT = "/api/v1/ai/assistant"


async def test_assistant_returns_case_grounded_cited_answer(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, summary="Victim lost 0.45 BTC to scam platform")

    response = await client.post(
        ASSISTANT,
        json={"case_id": case["id"], "task_type": "research_assistant",
              "input": "What do we know about the fund flow so far?"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["model"] == MODEL_REASONING, "research routes to the reasoning model (LD-24)"
    assert f"case:{case['id']}" in body["source_refs"]
    assert "case_core" in body["output"], "draft must be grounded in case context"

    entry = (
        await app_session.execute(
            select(AiCallLogEntry).where(AiCallLogEntry.id == body["ai_call_log_id"])
        )
    ).scalar_one()
    assert entry.status == "completed"
    assert entry.model_name == MODEL_REASONING
    assert len(entry.prompt_hash) == 64 and len(entry.response_hash) == 64
    assert entry.latency_ms is not None
    assert str(entry.case_id) == case["id"]


async def test_summarization_routes_to_formatting_model(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    response = await client.post(
        ASSISTANT,
        json={"case_id": case["id"], "task_type": "case_summarization",
              "input": "Summarize the case"},
        headers=idem_headers(tenant),
    )
    assert response.json()["model"] == MODEL_FORMATTING, "formatting-heavy → cheaper model"


async def test_failed_model_call_is_logged(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)

    response = await client.post(
        ASSISTANT,
        json={"case_id": case["id"], "task_type": "research_assistant",
              "input": "SIMULATE_MODEL_FAILURE"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 502

    failed = (
        (
            await app_session.execute(
                select(AiCallLogEntry).where(
                    AiCallLogEntry.case_id == uuid.UUID(case["id"]),
                    AiCallLogEntry.status == "failed",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(failed) == 1, "failures are logged too (no unlogged AI behavior)"
    assert failed[0].response_hash is None


async def test_assistant_requires_idempotency_key(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    response = await client.post(
        ASSISTANT,
        json={"case_id": case["id"], "input": "hello"},
        headers=tenant.headers,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_required"


async def test_assistant_unknown_task_type_rejected(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    response = await client.post(
        ASSISTANT,
        json={"case_id": case["id"], "task_type": "world_domination", "input": "x"},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 400


async def test_assistant_is_tenant_scoped(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)
    response = await client.post(
        ASSISTANT,
        json={"case_id": case_a["id"], "input": "cross-tenant probe"},
        headers=idem_headers(tenant_b),
    )
    assert response.status_code == 404
