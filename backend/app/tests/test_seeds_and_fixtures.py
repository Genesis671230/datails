"""Slice 0 acceptance: fixtures load.

- Bootstrap seeds the AQ baseline methodology (05 §2): 8 structured steps,
  human-approval gates on tracing findings, freeze letters, SAR, final report.
- The placeholder AQ case fixture loads into a workspace.
- Synthetic Crystal fixtures load and are marked provisional (LD-6).
"""

import uuid

import pytest
from sqlalchemy import select

from app.db.models import Methodology, MethodologyStep
from app.fixtures.aq_case import load_aq_case, read_fixture
from app.integrations.crystal.fixtures import FIXTURE_NAMES, load_crystal_fixture
from app.tests.auth_utils import mint_token
from app.tests.factories import create_tenant, create_user, create_workspace

APPROVAL_GATED_STEPS = {5, 6, 7, 8}  # tracing, freeze letter, SAR, final report


async def test_bootstrap_seeds_baseline_methodology(client, app_session) -> None:
    token = mint_token(str(uuid.uuid4()))
    response = await client.post(
        "/api/v1/workspaces/bootstrap", json={}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    tenant_id = uuid.UUID(response.json()["tenant"]["id"])

    methodology = (
        await app_session.execute(
            select(Methodology).where(Methodology.tenant_id == tenant_id)
        )
    ).scalar_one()
    steps = (
        (
            await app_session.execute(
                select(MethodologyStep)
                .where(MethodologyStep.methodology_id == methodology.id)
                .order_by(MethodologyStep.step_order)
            )
        )
        .scalars()
        .all()
    )
    assert len(steps) == 8
    assert steps[0].step_name == "Victim intake (five W's)"
    gated = {step.step_order for step in steps if step.requires_human_approval}
    assert gated == APPROVAL_GATED_STEPS, "human gates must match 05 §2 exactly"


async def test_aq_case_fixture_loads(app_session) -> None:
    tenant = await create_tenant(app_session)
    user = await create_user(app_session, tenant)
    workspace = await create_workspace(app_session, tenant)

    loaded = await load_aq_case(app_session, tenant, workspace, user)
    await app_session.commit()

    assert loaded.is_placeholder, "must be flagged until the real AQ dataset arrives"
    assert loaded.case.tenant_id == tenant.id
    assert set(loaded.wallets) == {"victim", "intermediary", "exchange_deposit"}
    assert len(loaded.expected_hops) == 2
    assert loaded.expected_hops[1]["boundary_flag"] == "hot_wallet"


async def test_aq_fixture_wallet_refs_are_consistent() -> None:
    data = read_fixture()
    wallet_refs = {w["ref"] for w in data["wallets"]}
    for hop in data["expected_hops"]:
        assert hop["from"] in wallet_refs
        assert hop["to"] in wallet_refs


def test_crystal_fixtures_load_and_are_provisional() -> None:
    for name in FIXTURE_NAMES:
        fixture = load_crystal_fixture(name)
        assert fixture["_provisional"] is True, "synthetic until the LD-6 spike"
        assert fixture["mode"] == name
        assert {"address", "chain", "risk_score", "risk_color"} <= fixture.keys()


def test_unknown_crystal_fixture_rejected() -> None:
    with pytest.raises(ValueError, match="unknown Crystal fixture"):
        load_crystal_fixture("does_not_exist")
