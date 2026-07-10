"""Slice 3 tests: the demonstrable loop on the placeholder AQ fixture.

Wallet in → Crystal enrichment (replay) → FIFO hop proposals → per-hop human
confirmation → hot-wallet boundary → exchange information request → explorer
graph → every step in the ledgers. Plus LD-27 state machine, rejection flow,
interrupt/resume, and the named case-memory acceptance test.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select

from app.db.models import DecisionLedgerEvent, WorkflowAgentRun
from app.fixtures.aq_case import load_aq_case
from app.integrations.generic_api.base import NormalizedTransfer
from app.services.traces.fifo import select_next_hop
from app.tests.helpers import bootstrap_tenant, idem_headers


async def _setup_aq(client, app_session, tenant):
    """Load the AQ fixture into the bootstrapped tenant's workspace and
    register the Crystal connector."""
    from app.db.models import Tenant, User, Workspace

    tenant_row = await app_session.get(Tenant, uuid.UUID(tenant.tenant_id))
    user_row = await app_session.get(User, uuid.UUID(tenant.user_id))
    workspace_row = await app_session.get(Workspace, uuid.UUID(tenant.workspace_id))
    loaded = await load_aq_case(app_session, tenant_row, workspace_row, user_row)
    await app_session.commit()

    await client.post(
        "/api/v1/connectors",
        json={"name": "Crystal", "connector_type": "crystal",
              "credential_owner": "datails_shared"},
        headers=tenant.headers,
    )
    return loaded


async def _create_trace(client, tenant, case_id: str, root_wallet_id: str) -> dict:
    response = await client.post(
        f"/api/v1/cases/{case_id}/traces",
        json={"root_wallet_id": root_wallet_id},
        headers=idem_headers(tenant),
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- FIFO engine unit tests -----------------------------------------------------


def _transfer(tx: str, direction: str, amount: str, ts: str) -> NormalizedTransfer:
    return NormalizedTransfer(
        tx_hash=tx, direction=direction, counterparty_address=f"addr-{tx}",
        asset="BTC", amount=amount, timestamp=ts,
    )


def test_fifo_picks_earliest_outgoing() -> None:
    candidate = select_next_hop(
        [
            _transfer("late", "out", "0.2", "2026-05-02T00:00:00Z"),
            _transfer("early", "out", "0.3", "2026-05-01T00:00:00Z"),
            _transfer("incoming", "in", "0.5", "2026-04-30T00:00:00Z"),
        ],
        tracked_amount=Decimal("0.5"),
        excluded_tx_hashes=frozenset(),
    )
    assert candidate.tx_hash == "early"
    assert candidate.amount == Decimal("0.3"), "min(tracked, transfer)"
    assert candidate.confidence == Decimal("0.75"), "ambiguity lowers confidence"


def test_fifo_single_candidate_high_confidence() -> None:
    candidate = select_next_hop(
        [_transfer("only", "out", "0.9", "2026-05-01T00:00:00Z")],
        tracked_amount=Decimal("0.4"),
        excluded_tx_hashes=frozenset(),
    )
    assert candidate.confidence == Decimal("0.95")
    assert candidate.amount == Decimal("0.4")


def test_fifo_respects_exclusions_and_exhaustion() -> None:
    transfers = [_transfer("a", "out", "0.1", "2026-05-01T00:00:00Z")]
    assert select_next_hop(
        transfers, tracked_amount=Decimal("1"), excluded_tx_hashes=frozenset({"a"})
    ) is None


# --- the demonstrable loop --------------------------------------------------------


async def test_full_aq_loop_to_hot_wallet_boundary(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    case_id = str(loaded.case.id)
    victim_wallet_id = str(loaded.wallets["victim"].id)

    # Hop 0 proposed from the victim wallet.
    trace = await _create_trace(client, tenant, case_id, victim_wallet_id)
    assert trace["status"] == "awaiting_confirmation"
    assert len(trace["hops"]) == 1
    hop0 = trace["hops"][0]
    assert hop0["status"] == "proposed"
    assert hop0["tx_hash"].endswith("0001")
    assert Decimal(hop0["amount"]) == Decimal("0.45")

    # Confirm hop 0 → hop 1 proposed (intermediary → exchange, boundary).
    after0 = (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/confirm",
            headers=tenant.headers,
        )
    ).json()
    assert after0["status"] == "awaiting_confirmation"
    hop1 = next(h for h in after0["hops"] if h["hop_index"] == 1)
    assert hop1["boundary_flag"] == "hot_wallet"
    assert Decimal(hop1["amount"]) == Decimal("0.44")
    assert hop1["evidence_refs_json"]["data_ledger_ids"], "hops are grounded in the ledger"

    # Confirm the boundary hop → traversal ends with the exchange request.
    final = (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop1['id']}/confirm",
            headers=tenant.headers,
        )
    ).json()
    assert final["status"] == "completed"
    assert final["run_output"]["recommendation"] == "exchange_information_request"
    assert "not further graph traversal" in final["run_output"]["note"]

    # Explorer graph: 3 nodes, 2 confirmed edges, labels with provenance.
    graph = final["graph"]
    assert len(graph["nodes"]) == 3
    assert len(graph["edges"]) == 2
    assert graph["attribution_method"] == "fifo"
    exchange_node = next(
        n for n in graph["nodes"] if any(lbl["label"] == "Binance" for lbl in n["labels"])
    )
    binance = next(lbl for lbl in exchange_node["labels"] if lbl["label"] == "Binance")
    assert binance["data_ledger_id"] is not None, "label provenance in the graph (LD-14)"

    # Every step in the ledgers: 2 hop confirmations as decision events.
    events = (
        (
            await app_session.execute(
                select(DecisionLedgerEvent).where(
                    DecisionLedgerEvent.case_id == loaded.case.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len([e for e in events if e.event_type.value == "approved"]) == 2
    data_ledger = (
        await client.get(f"/api/v1/ledger/data?case_id={case_id}", headers=tenant.headers)
    ).json()
    assert len(data_ledger) >= 4, "each proposal snapshots lookup + counterparty check"

    # LD-27: every transition recorded with timestamp + cause.
    transitions = final["run_output"]["transitions"]
    assert [t["to"] for t in transitions][:2] == ["running", "awaiting_confirmation"]
    assert transitions[-1]["to"] == "completed"
    assert all(t["at"] and t["cause"] for t in transitions)


async def test_reject_proposes_alternative_or_completes(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    trace = await _create_trace(
        client, tenant, str(loaded.case.id), str(loaded.wallets["victim"].id)
    )
    hop0 = trace["hops"][0]

    after = (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/reject",
            headers=tenant.headers,
        )
    ).json()
    # The victim wallet has exactly one outgoing transfer, so rejection
    # exhausts candidates and the run completes with the no-candidates
    # recommendation.
    assert after["status"] == "completed"
    assert after["run_output"]["recommendation"] == "no_further_candidates"
    rejected = next(h for h in after["hops"] if h["id"] == hop0["id"])
    assert rejected["status"] == "rejected"

    events = (
        (
            await app_session.execute(
                select(DecisionLedgerEvent).where(
                    DecisionLedgerEvent.case_id == loaded.case.id,
                    DecisionLedgerEvent.event_type == "rejected",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].approved is False


async def test_agent_never_proposes_past_unconfirmed_hop(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    trace = await _create_trace(
        client, tenant, str(loaded.case.id), str(loaded.wallets["victim"].id)
    )
    assert len([h for h in trace["hops"] if h["status"] == "proposed"]) == 1

    # A second create on the same case is a NEW trace (own run), but within a
    # trace there is never more than one open proposal.
    detail = (await client.get(f"/api/v1/traces/{trace['id']}", headers=tenant.headers)).json()
    assert len([h for h in detail["hops"] if h["status"] == "proposed"]) == 1


async def test_trace_creation_requires_idempotency_key_and_replays(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    case_id = str(loaded.case.id)
    wallet_id = str(loaded.wallets["victim"].id)

    missing = await client.post(
        f"/api/v1/cases/{case_id}/traces",
        json={"root_wallet_id": wallet_id},
        headers=tenant.headers,
    )
    assert missing.status_code == 400

    headers = idem_headers(tenant)
    first = await client.post(
        f"/api/v1/cases/{case_id}/traces", json={"root_wallet_id": wallet_id},
        headers=headers,
    )
    replay = await client.post(
        f"/api/v1/cases/{case_id}/traces", json={"root_wallet_id": wallet_id},
        headers=headers,
    )
    assert replay.headers.get("x-idempotent-replay") == "true"
    assert replay.json()["id"] == first.json()["id"], "no second trace created"


async def test_interrupt_and_resume_from_last_confirmed(client, app_session, monkeypatch) -> None:
    """LD-27: a proposal failure after confirmation leaves the run failed
    with the confirmed hop intact; re-confirming the last confirmed hop
    retries ONLY the proposal — no duplicate ledger events."""
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    trace = await _create_trace(
        client, tenant, str(loaded.case.id), str(loaded.wallets["victim"].id)
    )
    hop0 = trace["hops"][0]

    # Break the connector during the post-confirmation proposal.
    from app.services.traces import service as traces_service

    original = traces_service.wallet_lookup_and_attach

    async def failing(*args, **kwargs):
        raise RuntimeError("simulated connector outage")

    monkeypatch.setattr(traces_service, "wallet_lookup_and_attach", failing)
    interrupted = await client.post(
        f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/confirm",
        headers=tenant.headers,
    )
    assert interrupted.status_code == 500

    state = (await client.get(f"/api/v1/traces/{trace['id']}", headers=tenant.headers)).json()
    assert state["status"] == "failed"
    confirmed_hop = next(h for h in state["hops"] if h["id"] == hop0["id"])
    assert confirmed_hop["status"] == "confirmed", "confirmed work survives the failure"

    # Restore the connector; resume by re-confirming the last confirmed hop.
    monkeypatch.setattr(traces_service, "wallet_lookup_and_attach", original)
    resumed = (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/confirm",
            headers=tenant.headers,
        )
    ).json()
    assert resumed["status"] == "awaiting_confirmation"
    assert any(h["hop_index"] == 1 for h in resumed["hops"]), "proposal retried"

    # Exactly ONE approval event for hop 0 — confirmed work never re-executes.
    events = (
        (
            await app_session.execute(
                select(DecisionLedgerEvent).where(
                    DecisionLedgerEvent.case_id == loaded.case.id,
                    DecisionLedgerEvent.event_type == "approved",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


async def test_case_memory_across_sessions(client, app_session) -> None:
    """Named acceptance test (07 Slice 3): close session → reopen case →
    full context (wallets, hops, findings, drafts) present without re-entry.

    'Session close' = a fresh HTTP client and a cleared context cache; the
    only state carrier is the database.
    """
    from httpx import ASGITransport, AsyncClient

    from app.services.ai.context_builder import clear_context_cache

    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    case_id = str(loaded.case.id)

    # Work: trace two hops to the boundary, add a finding, draft a report.
    trace = await _create_trace(
        client, tenant, case_id, str(loaded.wallets["victim"].id)
    )
    hop0 = trace["hops"][0]
    after0 = (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/confirm",
            headers=tenant.headers,
        )
    ).json()
    hop1 = next(h for h in after0["hops"] if h["hop_index"] == 1)
    await client.post(
        f"/api/v1/traces/{trace['id']}/hops/{hop1['id']}/confirm", headers=tenant.headers
    )
    await client.post(
        "/api/v1/findings",
        json={"case_id": case_id, "finding_type": "wallet_attribution",
              "title": "Deposit belongs to Binance"},
        headers=tenant.headers,
    )
    draft = await client.post(
        "/api/v1/reports/draft",
        json={"case_id": case_id, "report_type": "freeze_blocklist_request",
              "title": "Freeze — Binance", "jurisdiction": "DE"},
        headers=idem_headers(tenant),
    )
    report_id = draft.json()["report"]["id"]

    # "Close the session": new client, cold caches. Same identity token.
    clear_context_cache()
    transport = ASGITransport(app=client._transport.app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as fresh:
        detail = (await fresh.get(f"/api/v1/cases/{case_id}", headers=tenant.headers)).json()
        assert len(detail["wallets"]) == 3, "wallets persisted"
        assert len(detail["findings"]) == 1, "findings persisted"

        reopened_trace = (
            await fresh.get(f"/api/v1/traces/{trace['id']}", headers=tenant.headers)
        ).json()
        assert reopened_trace["status"] == "completed"
        assert len(reopened_trace["graph"]["edges"]) == 2, "confirmed hops persisted"

        report = (
            await fresh.get(f"/api/v1/reports/{report_id}", headers=tenant.headers)
        ).json()
        assert report["status"] == "draft", "draft persisted"

        # The assistant sees the full context without re-entry.
        answer = (
            await fresh.post(
                "/api/v1/ai/assistant",
                json={"case_id": case_id, "task_type": "research_assistant",
                      "input": "Where does the trace currently end?"},
                headers=idem_headers(tenant),
            )
        ).json()
        assert any(ref.startswith("data_ledger:") for ref in answer["source_refs"]), (
            "reopened context carries label provenance refs"
        )


async def test_traces_are_tenant_isolated(client, app_session) -> None:
    tenant_a = await bootstrap_tenant(client)
    tenant_b = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant_a)
    trace = await _create_trace(
        client, tenant_a, str(loaded.case.id), str(loaded.wallets["victim"].id)
    )
    hop0 = trace["hops"][0]

    assert (
        await client.get(f"/api/v1/traces/{trace['id']}", headers=tenant_b.headers)
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/traces/{trace['id']}/hops/{hop0['id']}/confirm",
            headers=tenant_b.headers,
        )
    ).status_code == 404


async def test_trace_run_recorded_in_workflow_agent_runs(client, app_session) -> None:
    tenant = await bootstrap_tenant(client)
    loaded = await _setup_aq(client, app_session, tenant)
    trace = await _create_trace(
        client, tenant, str(loaded.case.id), str(loaded.wallets["victim"].id)
    )
    run = await app_session.get(WorkflowAgentRun, uuid.UUID(trace["workflow_agent_run_id"]))
    assert run is not None
    assert run.task_type == "fund_flow_trace"
    assert run.status.value == "awaiting_confirmation"
    assert run.started_at is not None
