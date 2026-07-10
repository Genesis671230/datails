"""Golden-set smoke test (LD-29).

Fixed cases with expected report-draft properties, run on any prompt or
model-routing change. Asserts structural draft properties (grounding,
citations, routing, status), not exact wording — stable across the mock
backend now and the live Foundry backend later.
"""

import pytest

from app.services.ai.model_router import MODEL_REASONING
from app.tests.helpers import bootstrap_tenant, create_case, idem_headers

# The golden set: case setup → report request → expected draft properties.
GOLDEN_CASES = (
    {
        "id": "golden-1-freeze-request",
        "case": {"title": "Investment scam — BTC to CEX deposit",
                 "summary": "0.44 BTC traced to exchange deposit address."},
        "report": {"report_type": "freeze_blocklist_request",
                   "title": "Freeze request — exchange", "jurisdiction": "DE"},
        "expect_model": MODEL_REASONING,
    },
    {
        "id": "golden-2-sar-draft",
        "case": {"title": "Suspicious flow — layering pattern",
                 "summary": "Multiple rapid transfers through fresh wallets."},
        "report": {"report_type": "sar_draft", "title": "SAR draft",
                   "jurisdiction": "AT"},
        "expect_model": MODEL_REASONING,
    },
    {
        "id": "golden-3-police-intake",
        "case": {"title": "Romance scam intake",
                 "summary": "Victim intake per the five W's completed."},
        "report": {"report_type": "police_intake", "title": "Police intake report",
                   "jurisdiction": "DE"},
        "expect_model": MODEL_REASONING,
    },
    {
        "id": "golden-4-investigator-summary",
        "case": {"title": "Ongoing trace — status summary",
                 "summary": "Two confirmed hops; hot-wallet boundary reached."},
        "report": {"report_type": "investigator_summary", "title": "Status summary"},
        "expect_model": MODEL_REASONING,
    },
)


@pytest.mark.parametrize("golden", GOLDEN_CASES, ids=[g["id"] for g in GOLDEN_CASES])
async def test_golden_report_draft_properties(client, golden) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(client, tenant, **golden["case"])

    response = await client.post(
        "/api/v1/reports/draft",
        json={"case_id": case["id"], **golden["report"]},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 201, response.text
    body = response.json()

    report, version = body["report"], body["version"]
    # Draft-by-default and versioned.
    assert report["status"] == "draft"
    assert version["version_number"] == 1
    assert version["generated_by_ai"] is True
    # Grounded and cited: the case itself is always a source ref, and the
    # draft content reflects the case context sections.
    refs = version["source_refs_json"]["refs"]
    assert f"case:{case['id']}" in refs
    assert "case_core" in version["content_markdown"]
    # Jurisdiction recorded when requested.
    expected_jurisdiction = golden["report"].get("jurisdiction")
    assert report["jurisdiction"] == expected_jurisdiction


async def test_golden_assistant_answer_properties(client) -> None:
    tenant = await bootstrap_tenant(client)
    case = await create_case(
        client, tenant,
        title="Golden assistant case",
        summary="Funds moved from victim wallet to intermediary.",
    )
    response = await client.post(
        "/api/v1/ai/assistant",
        json={"case_id": case["id"], "task_type": "research_assistant",
              "input": "Summarize the confirmed fund flow."},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source_refs"], "assistant answers must carry source references"
    assert body["model"] == MODEL_REASONING
