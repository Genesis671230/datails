"""LD-5 tests: inclusion priority, budget truncation, cache behavior,
source refs, no raw payloads."""

import uuid

import pytest

from app.core.errors import NotFoundError
from app.services.ai.context_builder import (
    build_case_context,
    clear_context_cache,
)
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_context_cache()
    yield
    clear_context_cache()


async def _tenant_uuid(tenant) -> uuid.UUID:
    return uuid.UUID(tenant.tenant_id)


async def test_context_includes_core_and_emits_refs(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, summary="Victim lost 0.45 BTC")

    context = await build_case_context(
        app_session, await _tenant_uuid(tenant), uuid.UUID(case["id"]), "research_assistant"
    )
    assert "## case_core" in context.text
    assert "Victim lost 0.45 BTC" in context.text
    assert f"case:{case['id']}" in context.source_refs
    assert context.token_estimate > 0


async def test_context_orders_sections_by_priority(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    await client.post(
        "/api/v1/decisions",
        json={"case_id": case["id"], "decision_type": "open_case", "description": "Opened"},
        headers=tenant.headers,
    )
    await client.post(
        f"/api/v1/cases/{case['id']}/evidence",
        json={"evidence_type": "screenshot", "title": "Chat screenshot"},
        headers=tenant.headers,
    )

    context = await build_case_context(
        app_session, await _tenant_uuid(tenant), uuid.UUID(case["id"]), "research_assistant"
    )
    text = context.text
    assert text.index("## case_core") < text.index("## decisions") < text.index(
        "## evidence_refs"
    )
    # Evidence lines carry references/titles only, never payload content.
    assert "Chat screenshot" in text
    assert "## methodology_cues" in text, "baseline methodology cues present"


async def test_wallet_labels_carry_provenance_refs(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    await client.post(
        "/api/v1/connectors",
        json={"name": "Crystal", "connector_type": "crystal",
              "credential_owner": "datails_shared"},
        headers=tenant.headers,
    )
    attach = await client.post(
        "/api/v1/connectors/crystal/wallet-lookup-and-attach",
        json={"case_id": case["id"], "address": "bc1qctx", "chain": "bitcoin",
              "mode": "risk_check"},
        headers=idem_headers(tenant),
    )
    ledger_id = attach.json()["data_ledger_id"]

    context = await build_case_context(
        app_session, await _tenant_uuid(tenant), uuid.UUID(case["id"]), "research_assistant"
    )
    assert f"Binance [data_ledger:{ledger_id}]" in context.text
    assert f"data_ledger:{ledger_id}" in context.source_refs


async def test_truncation_drops_lowest_priority_sections_first(
    client, app_session, monkeypatch
) -> None:
    from app.services.ai import model_router

    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, summary="s" * 400)
    # Draft finding (lowest priority) + evidence.
    await client.post(
        "/api/v1/findings",
        json={"case_id": case["id"], "finding_type": "other", "title": "Draft",
              "content": "d" * 400},
        headers=tenant.headers,
    )

    tiny = model_router.TaskRoute("research_assistant", model_router.MODEL_REASONING,
                                  context_budget_tokens=150)
    monkeypatch.setattr(model_router, "_ROUTES", {**model_router._ROUTES,
                                                  "research_assistant": tiny})
    context = await build_case_context(
        app_session, await _tenant_uuid(tenant), uuid.UUID(case["id"]), "research_assistant"
    )
    assert "draft_findings" in context.truncated_sections
    assert "## case_core" in context.text, "case core survives truncation"


async def test_cache_hit_and_invalidation_on_write(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    tenant_id = await _tenant_uuid(tenant)
    case_id = uuid.UUID(case["id"])

    first = await build_case_context(app_session, tenant_id, case_id, "research_assistant")
    second = await build_case_context(app_session, tenant_id, case_id, "research_assistant")
    assert second is first, "unchanged case graph must serve the cached object"

    await client.post(
        "/api/v1/decisions",
        json={"case_id": case["id"], "decision_type": "open_case", "description": "New"},
        headers=tenant.headers,
    )
    third = await build_case_context(app_session, tenant_id, case_id, "research_assistant")
    assert third is not first, "a case-graph write must invalidate the cache"
    assert "New" in third.text


async def test_unknown_task_type_rejected(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    with pytest.raises(ValueError, match="unknown AI task type"):
        await build_case_context(
            app_session, await _tenant_uuid(tenant), uuid.UUID(case["id"]), "bogus"
        )


async def test_context_is_tenant_scoped(client, app_session) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)
    with pytest.raises(NotFoundError):
        await build_case_context(
            app_session, await _tenant_uuid(tenant_b), uuid.UUID(case_a["id"]),
            "research_assistant",
        )
