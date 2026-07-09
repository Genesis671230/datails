"""Case domain integration tests (Slice 1).

Covers the Phase 5 route surface, the LD-8 detail shape (findings + decisions
explicit), LD-13 workspace-global wallet behavior, and LD-10 tenant isolation.
"""

import uuid

from app.tests.helpers import bootstrap_tenant, create_case

BTC_ADDRESS = "bc1qtestwallet0000000000000000000000000001"


async def test_create_and_get_case_detail(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, summary="Victim lost 0.45 BTC")

    response = await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)
    assert response.status_code == 200
    detail = response.json()
    assert detail["title"] == "Investment scam — victim intake"
    assert detail["status"] == "open"
    # LD-8: coherent state includes findings and decisions explicitly.
    assert detail["findings"] == []
    assert detail["decisions"] == []
    assert detail["wallets"] == []
    assert detail["evidence"] == []


async def test_list_cases_newest_first(client) -> None:
    tenant = await bootstrap_tenant(client)
    first = await create_case(client, tenant, title="Older case")
    second = await create_case(client, tenant, title="Newer case")

    response = await client.get("/api/v1/cases", headers=tenant.headers)
    ids = [c["id"] for c in response.json()]
    assert ids.index(second["id"]) < ids.index(first["id"])


async def test_update_case(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)

    response = await client.put(
        f"/api/v1/cases/{case['id']}",
        json={"status": "active", "priority": "urgent", "summary": "Escalated"},
        headers=tenant.headers,
    )
    assert response.status_code == 200
    updated = response.json()
    assert (updated["status"], updated["priority"]) == ("active", "urgent")


async def test_invalid_case_type_rejected(client) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        "/api/v1/cases",
        json={"title": "x", "case_type": "not_a_type"},
        headers=tenant.headers,
    )
    assert response.status_code == 422


async def test_attach_wallet_and_reuse_across_cases(client) -> None:
    """LD-13: the same address in two cases resolves to ONE workspace wallet."""
    tenant = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant, title="Case A")
    case_b = await create_case(client, tenant, title="Case B")

    body = {"address": BTC_ADDRESS, "chain": "bitcoin", "role_in_case": "victim"}
    wallet_a = (
        await client.post(
            f"/api/v1/cases/{case_a['id']}/wallets", json=body, headers=tenant.headers
        )
    ).json()
    wallet_b = (
        await client.post(
            f"/api/v1/cases/{case_b['id']}/wallets",
            json={**body, "role_in_case": "suspect"},
            headers=tenant.headers,
        )
    ).json()
    assert wallet_a["id"] == wallet_b["id"], "workspace-global wallet must be reused"
    assert wallet_b["role_in_case"] == "suspect", "role is per-case on the link"


async def test_attach_same_wallet_twice_is_idempotent(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)
    body = {"address": BTC_ADDRESS, "chain": "bitcoin"}

    first = await client.post(
        f"/api/v1/cases/{case['id']}/wallets", json=body, headers=tenant.headers
    )
    second = await client.post(
        f"/api/v1/cases/{case['id']}/wallets", json=body, headers=tenant.headers
    )
    assert first.json()["id"] == second.json()["id"]

    detail = (await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)).json()
    assert len(detail["wallets"]) == 1


async def test_add_evidence(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)

    response = await client.post(
        f"/api/v1/cases/{case['id']}/evidence",
        json={
            "evidence_type": "transaction_history_export",
            "title": "Kraken export March–May",
            "source_ref": "victim-email-2026-07-01",
        },
        headers=tenant.headers,
    )
    assert response.status_code == 201
    detail = (await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)).json()
    assert len(detail["evidence"]) == 1
    assert detail["evidence"][0]["evidence_type"] == "transaction_history_export"


async def test_create_finding_appears_in_case_detail(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant)

    response = await client.post(
        "/api/v1/findings",
        json={
            "case_id": case["id"],
            "finding_type": "wallet_attribution",
            "title": "Deposit address belongs to exchange",
            "confidence": "0.90",
        },
        headers=tenant.headers,
    )
    assert response.status_code == 201
    assert response.json()["is_ai_generated"] is False

    detail = (await client.get(f"/api/v1/cases/{case['id']}", headers=tenant.headers)).json()
    assert len(detail["findings"]) == 1


async def test_finding_for_missing_case_404(client) -> None:
    tenant = await bootstrap_tenant(client)
    response = await client.post(
        "/api/v1/findings",
        json={"case_id": str(uuid.uuid4()), "finding_type": "other", "title": "x"},
        headers=tenant.headers,
    )
    assert response.status_code == 404


# --- LD-10 tenant isolation --------------------------------------------------


async def test_cases_are_tenant_isolated(client) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    case_a = await create_case(client, tenant_a)

    get_cross = await client.get(f"/api/v1/cases/{case_a['id']}", headers=tenant_b.headers)
    assert get_cross.status_code == 404

    update_cross = await client.put(
        f"/api/v1/cases/{case_a['id']}", json={"status": "closed"}, headers=tenant_b.headers
    )
    assert update_cross.status_code == 404

    evidence_cross = await client.post(
        f"/api/v1/cases/{case_a['id']}/evidence",
        json={"evidence_type": "other", "title": "x"},
        headers=tenant_b.headers,
    )
    assert evidence_cross.status_code == 404

    finding_cross = await client.post(
        "/api/v1/findings",
        json={"case_id": case_a["id"], "finding_type": "other", "title": "x"},
        headers=tenant_b.headers,
    )
    assert finding_cross.status_code == 404

    list_b = (await client.get("/api/v1/cases", headers=tenant_b.headers)).json()
    assert case_a["id"] not in [c["id"] for c in list_b]
