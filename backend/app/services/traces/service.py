"""Trace orchestration: the pilot's demonstrable loop (05 §8, LD-27).

Loop: create trace → engine proposes one hop (FIFO, from connector data) →
investigator confirms or rejects → engine proposes the next → … until a
hot-wallet boundary ends traversal and the run proposes an exchange
information request instead of further graph traversal.

Rules enforced here:
- The agent never proposes past an unconfirmed hop (one open proposal max).
- A hop confirmation writes a decision_ledger event in the same transaction
  (LD-9 pattern) plus a consent-gated learning event (LD-30).
- State machine per LD-27 with every transition recorded (timestamp + cause)
  in the workflow_agent_run. awaiting_confirmation has no timeout — human
  pace is the design.
- Resume-from-last-confirmed (LD-27): a proposal failure marks the run
  `failed` WITHOUT touching confirmed hops; re-POSTing confirm on the last
  confirmed hop retries the proposal only — confirmed work is never
  re-executed, unconfirmed proposals are never silently retried.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger, log_fields
from app.db.models import (
    Trace,
    TraceHop,
    Wallet,
    WorkflowAgent,
    WorkflowAgentRun,
)
from app.db.models.enums import (
    AgentType,
    BoundaryFlag,
    ConnectorType,
    DecisionLedgerEventType,
    LearningEventType,
    RunStatus,
    TraceHopStatus,
    WalletKind,
)
from app.db.repositories.cases import get_case
from app.schemas.connectors import WalletLookupAndAttachRequest
from app.services.connectors.wallet_lookup import wallet_lookup_and_attach
from app.services.ledgers.learning import capture_learning_event
from app.services.ledgers.writers import write_decision_event
from app.services.traces.fifo import select_next_hop

logger = get_logger(__name__)

RESEARCH_ANALYST_NAME = "Research Analyst"

RECOMMENDATION_EXCHANGE_REQUEST = "exchange_information_request"
RECOMMENDATION_NO_CANDIDATES = "no_further_candidates"


# --- workflow agent plumbing ---------------------------------------------------


async def _get_or_create_research_analyst(
    session: AsyncSession, tenant_id: UUID, workspace_id: UUID
) -> WorkflowAgent:
    result = await session.execute(
        select(WorkflowAgent).where(
            WorkflowAgent.tenant_id == tenant_id,
            WorkflowAgent.workspace_id == workspace_id,
            WorkflowAgent.agent_type == AgentType.RESEARCH_ANALYST,
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        agent = WorkflowAgent(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            agent_type=AgentType.RESEARCH_ANALYST,
            name=RESEARCH_ANALYST_NAME,
            description="Human-led fund-flow tracing under FIFO attribution.",
            role_instructions=(
                "Propose one hop at a time from connector transfer data; never "
                "past an unconfirmed hop; hot-wallet boundary ends traversal "
                "and proposes an exchange information request."
            ),
            allowed_tools_json={"tools": ["crystal"]},
            allowed_actions_json={"actions": ["propose_hop"]},
            approval_required=True,
        )
        session.add(agent)
        await session.flush()
    return agent


async def _transition(
    session: AsyncSession, run: WorkflowAgentRun, trace: Trace, to: RunStatus, cause: str
) -> None:
    """Record a state transition on run + trace (LD-27: timestamp + cause)."""
    transitions = list((run.output_ref_json or {}).get("transitions", []))
    transitions.append(
        {
            "from": run.status.value,
            "to": to.value,
            "cause": cause,
            "at": datetime.now(UTC).isoformat(),
        }
    )
    run.output_ref_json = {**(run.output_ref_json or {}), "transitions": transitions}
    run.status = to
    trace.status = to
    if to == RunStatus.RUNNING and run.started_at is None:
        run.started_at = datetime.now(UTC)
    if to in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.ABANDONED):
        run.completed_at = datetime.now(UTC)
    await session.flush()


def _set_recommendation(run: WorkflowAgentRun, recommendation: str, detail: dict) -> None:
    run.output_ref_json = {
        **(run.output_ref_json or {}),
        "recommendation": recommendation,
        **detail,
    }


# --- lookups -------------------------------------------------------------------


async def _get_trace(session: AsyncSession, tenant_id: UUID, trace_id: UUID) -> Trace:
    result = await session.execute(
        select(Trace).where(Trace.id == trace_id, Trace.tenant_id == tenant_id)
    )
    trace = result.scalar_one_or_none()
    if trace is None:
        raise NotFoundError("Trace not found.")
    return trace


async def _get_run(session: AsyncSession, trace: Trace) -> WorkflowAgentRun:
    run = await session.get(WorkflowAgentRun, trace.workflow_agent_run_id)
    if run is None:
        raise NotFoundError("Trace has no workflow agent run.")
    return run


async def list_hops(session: AsyncSession, tenant_id: UUID, trace_id: UUID) -> list[TraceHop]:
    result = await session.execute(
        select(TraceHop)
        .where(TraceHop.trace_id == trace_id, TraceHop.tenant_id == tenant_id)
        .order_by(TraceHop.hop_index, TraceHop.created_at)
    )
    return list(result.scalars())


def _open_proposal(hops: list[TraceHop]) -> TraceHop | None:
    return next((h for h in hops if h.status == TraceHopStatus.PROPOSED), None)


def _confirmed(hops: list[TraceHop]) -> list[TraceHop]:
    return [h for h in hops if h.status == TraceHopStatus.CONFIRMED]


# --- boundary detection ----------------------------------------------------------


def _is_hot_wallet_boundary(wallet: Wallet, labels: list) -> bool:
    """Hot-wallet boundary: exchange entity label or hot_wallet kind [02-16]."""
    if wallet.wallet_kind == WalletKind.HOT_WALLET:
        return True
    return any(label.label_type.value == "entity" for label in labels)


# --- proposal step ---------------------------------------------------------------


async def _propose_next_hop(
    session: AsyncSession,
    trace: Trace,
    run: WorkflowAgentRun,
    user_id: UUID,
    *,
    from_wallet: Wallet,
    tracked_amount: Decimal,
    hop_index: int,
) -> TraceHop | None:
    """One engine step: connector lookup on the current wallet, FIFO
    selection, counterparty enrichment, proposal row.

    Returns None when no candidates remain (run completes with a
    recommendation). Raises on connector failure — caller records the
    failed transition with a resumable checkpoint.
    """
    hops = await list_hops(session, trace.tenant_id, trace.id)
    excluded = frozenset(
        h.tx_hash for h in hops if h.status == TraceHopStatus.REJECTED
    ) | frozenset(h.tx_hash for h in _confirmed(hops))

    # Deep lookup on the current wallet (LD-4 pipeline; case-attached).
    outcome, _ = await wallet_lookup_and_attach(
        session,
        trace.tenant_id,
        user_id,
        ConnectorType.CRYSTAL,
        WalletLookupAndAttachRequest(
            case_id=trace.case_id,
            address=from_wallet.address,
            chain=from_wallet.chain,
            mode="full_investigation",
        ),
    )

    candidate = select_next_hop(
        outcome.result.transfers,
        tracked_amount=tracked_amount,
        excluded_tx_hashes=excluded,
    )
    if candidate is None:
        return None

    # Enrich the counterparty (risk check → labels with provenance, LD-14)
    # and attach it to the case (a wallet seen here surfaces in other cases,
    # LD-13).
    counterparty_outcome, counterparty = await wallet_lookup_and_attach(
        session,
        trace.tenant_id,
        user_id,
        ConnectorType.CRYSTAL,
        WalletLookupAndAttachRequest(
            case_id=trace.case_id,
            address=candidate.to_address,
            chain=from_wallet.chain,
            mode="risk_check",
        ),
    )
    boundary = (
        BoundaryFlag.HOT_WALLET
        if _is_hot_wallet_boundary(counterparty, counterparty_outcome.result.labels)
        else None
    )
    if boundary is BoundaryFlag.HOT_WALLET and counterparty.wallet_kind is None:
        counterparty.wallet_kind = WalletKind.HOT_WALLET

    hop = TraceHop(
        trace_id=trace.id,
        tenant_id=trace.tenant_id,
        hop_index=hop_index,
        from_wallet_id=from_wallet.id,
        to_wallet_id=counterparty.id,
        tx_hash=candidate.tx_hash,
        asset=candidate.asset,
        chain=from_wallet.chain,
        amount=candidate.amount,
        confidence=candidate.confidence,
        evidence_refs_json={
            "data_ledger_ids": [outcome.ledger_entry.id, counterparty_outcome.ledger_entry.id]
        },
        boundary_flag=boundary,
        status=TraceHopStatus.PROPOSED,
    )
    session.add(hop)
    await session.flush()
    return hop


# --- public operations -------------------------------------------------------------


async def create_trace(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    *,
    case_id: UUID,
    root_wallet_id: UUID,
) -> Trace:
    """Start a trace: run row, then the first proposal."""
    case = await get_case(session, tenant_id, case_id)
    if case is None:
        raise NotFoundError("Case not found.")
    root_wallet = await session.get(Wallet, root_wallet_id)
    if root_wallet is None or root_wallet.tenant_id != tenant_id:
        raise NotFoundError("Root wallet not found.")

    agent = await _get_or_create_research_analyst(session, tenant_id, case.workspace_id)
    run = WorkflowAgentRun(
        workflow_agent_id=agent.id,
        tenant_id=tenant_id,
        workspace_id=case.workspace_id,
        case_id=case_id,
        task_type="fund_flow_trace",
        input_ref_json={"root_wallet_id": str(root_wallet_id), "attribution": "fifo"},
    )
    session.add(run)
    await session.flush()
    trace = Trace(
        tenant_id=tenant_id,
        workspace_id=case.workspace_id,
        case_id=case_id,
        root_wallet_id=root_wallet_id,
        workflow_agent_run_id=run.id,
        created_by=user_id,
    )
    session.add(trace)
    await session.flush()

    await _transition(session, run, trace, RunStatus.RUNNING, "trace created")
    try:
        hop = await _propose_next_hop(
            session, trace, run, user_id,
            from_wallet=root_wallet,
            # Until the real AQ dataset defines the stolen amount, track the
            # full first candidate (engine takes min(tracked, transfer)).
            tracked_amount=Decimal("1e18"),
            hop_index=0,
        )
    except Exception as exc:
        await _transition(session, run, trace, RunStatus.FAILED,
                          f"proposal failed: {exc}")
        await session.commit()
        raise

    if hop is None:
        _set_recommendation(run, RECOMMENDATION_NO_CANDIDATES,
                            {"wallet_id": str(root_wallet_id)})
        await _transition(session, run, trace, RunStatus.COMPLETED,
                          "no outgoing candidates from root wallet")
    else:
        await _transition(session, run, trace, RunStatus.AWAITING_CONFIRMATION,
                          f"hop {hop.hop_index} proposed")
    await session.commit()
    logger.info(
        "trace created",
        extra=log_fields(module="traces", action="create", status="ok",
                         case_id=str(case_id)),
    )
    return trace


async def get_trace_state(
    session: AsyncSession, tenant_id: UUID, trace_id: UUID
) -> tuple[Trace, WorkflowAgentRun, list[TraceHop]]:
    trace = await _get_trace(session, tenant_id, trace_id)
    run = await _get_run(session, trace)
    hops = await list_hops(session, tenant_id, trace_id)
    return trace, run, hops


async def confirm_hop(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, trace_id: UUID, hop_id: UUID
) -> tuple[Trace, TraceHop]:
    """Confirm a proposed hop; ledger event same-transaction; propose next.

    Resume path (LD-27): confirming an ALREADY-CONFIRMED hop retries the next
    proposal if none is open — confirmed work is never re-executed.
    """
    trace = await _get_trace(session, tenant_id, trace_id)
    run = await _get_run(session, trace)
    hops = await list_hops(session, tenant_id, trace_id)
    hop = next((h for h in hops if h.id == hop_id), None)
    if hop is None:
        raise NotFoundError("Hop not found.")

    if hop.status == TraceHopStatus.REJECTED:
        raise ConflictError("Hop was rejected; it cannot be confirmed.")

    if hop.status == TraceHopStatus.PROPOSED:
        hop.status = TraceHopStatus.CONFIRMED
        hop.confirmed_by = user_id
        hop.confirmed_at = datetime.now(UTC)
        # LD-9 pattern: ledger event in the same transaction as the confirmation.
        await write_decision_event(
            session,
            tenant_id=tenant_id,
            workspace_id=trace.workspace_id,
            case_id=trace.case_id,
            decision_id=None,
            event_type=DecisionLedgerEventType.APPROVED,
            actor_id=user_id,
            actor_type="user",
            inputs_ref={"trace_id": str(trace.id), "hop_id": str(hop.id),
                        "tx_hash": hop.tx_hash},
            approved=True,
        )
        await capture_learning_event(
            session,
            tenant_id=tenant_id,
            workspace_id=trace.workspace_id,
            case_id=trace.case_id,
            actor_id=user_id,
            event_type=LearningEventType.TRACE_HOP_CONFIRMED,
            subject_type="trace_hop",
            subject_id=str(hop.id),
            payload={"hop_index": hop.hop_index, "confidence": str(hop.confidence)},
        )
    elif _open_proposal(hops) is not None:
        raise ConflictError("Hop is already confirmed and a proposal is open.")

    # Hot-wallet boundary: traversal ends; propose the exchange information
    # request instead of further graph hops (05 §3/§8).
    if hop.boundary_flag == BoundaryFlag.HOT_WALLET:
        to_wallet = await session.get(Wallet, hop.to_wallet_id)
        _set_recommendation(
            run,
            RECOMMENDATION_EXCHANGE_REQUEST,
            {
                "boundary_hop_id": str(hop.id),
                "boundary_tx_hash": hop.tx_hash,
                "exchange_wallet_id": str(hop.to_wallet_id),
                "exchange_address": to_wallet.address if to_wallet else None,
                "note": (
                    "Trace boundary reached: last transaction hash into the hot "
                    "wallet. Next step is an information request to the "
                    "exchange, not further graph traversal."
                ),
            },
        )
        await _transition(session, run, trace, RunStatus.COMPLETED,
                          "hot-wallet boundary reached")
        await session.commit()
        return trace, hop

    # Propose the next hop from the confirmed destination.
    to_wallet = await session.get(Wallet, hop.to_wallet_id)
    try:
        next_hop = await _propose_next_hop(
            session, trace, run, user_id,
            from_wallet=to_wallet,
            tracked_amount=hop.amount,
            hop_index=hop.hop_index + 1,
        )
    except Exception as exc:
        await _transition(session, run, trace, RunStatus.FAILED,
                          f"proposal after hop {hop.hop_index} failed: {exc}")
        await session.commit()
        raise

    if next_hop is None:
        _set_recommendation(run, RECOMMENDATION_NO_CANDIDATES,
                            {"wallet_id": str(hop.to_wallet_id)})
        await _transition(session, run, trace, RunStatus.COMPLETED,
                          "no further outgoing candidates")
    else:
        await _transition(session, run, trace, RunStatus.AWAITING_CONFIRMATION,
                          f"hop {next_hop.hop_index} proposed")
    await session.commit()
    return trace, hop


async def reject_hop(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, trace_id: UUID, hop_id: UUID
) -> tuple[Trace, TraceHop]:
    """Reject a proposed hop; the engine tries the next FIFO candidate from
    the same wallet (rejected tx hashes excluded)."""
    trace = await _get_trace(session, tenant_id, trace_id)
    run = await _get_run(session, trace)
    hops = await list_hops(session, tenant_id, trace_id)
    hop = next((h for h in hops if h.id == hop_id), None)
    if hop is None:
        raise NotFoundError("Hop not found.")
    if hop.status != TraceHopStatus.PROPOSED:
        raise ConflictError(f"Only proposed hops can be rejected (hop is {hop.status.value}).")

    hop.status = TraceHopStatus.REJECTED
    hop.confirmed_by = user_id
    hop.confirmed_at = datetime.now(UTC)
    await write_decision_event(
        session,
        tenant_id=tenant_id,
        workspace_id=trace.workspace_id,
        case_id=trace.case_id,
        decision_id=None,
        event_type=DecisionLedgerEventType.REJECTED,
        actor_id=user_id,
        actor_type="user",
        inputs_ref={"trace_id": str(trace.id), "hop_id": str(hop.id),
                    "tx_hash": hop.tx_hash},
        approved=False,
    )
    await capture_learning_event(
        session,
        tenant_id=tenant_id,
        workspace_id=trace.workspace_id,
        case_id=trace.case_id,
        actor_id=user_id,
        event_type=LearningEventType.TRACE_HOP_REJECTED,
        subject_type="trace_hop",
        subject_id=str(hop.id),
        payload={"hop_index": hop.hop_index},
    )

    from_wallet = await session.get(Wallet, hop.from_wallet_id)
    confirmed = _confirmed(hops)
    tracked = confirmed[-1].amount if confirmed else Decimal("1e18")
    try:
        next_hop = await _propose_next_hop(
            session, trace, run, user_id,
            from_wallet=from_wallet,
            tracked_amount=tracked,
            hop_index=hop.hop_index,
        )
    except Exception as exc:
        await _transition(session, run, trace, RunStatus.FAILED,
                          f"proposal after rejection failed: {exc}")
        await session.commit()
        raise

    if next_hop is None:
        _set_recommendation(run, RECOMMENDATION_NO_CANDIDATES,
                            {"wallet_id": str(hop.from_wallet_id)})
        await _transition(session, run, trace, RunStatus.COMPLETED,
                          "no alternative candidates after rejection")
    else:
        await _transition(session, run, trace, RunStatus.AWAITING_CONFIRMATION,
                          f"alternative hop {next_hop.hop_index} proposed")
    await session.commit()
    return trace, hop


# --- graph output (transaction explorer) --------------------------------------------


async def build_graph(
    session: AsyncSession, tenant_id: UUID, trace_id: UUID
) -> dict:
    """Nodes = wallets with current labels + provenance; edges = confirmed
    hops with confidence (07 Slice 3)."""
    from app.db.repositories.wallets import get_current_labels

    trace = await _get_trace(session, tenant_id, trace_id)
    hops = await list_hops(session, tenant_id, trace_id)
    confirmed = _confirmed(hops)

    wallet_ids = {trace.root_wallet_id}
    for hop in confirmed:
        wallet_ids.update((hop.from_wallet_id, hop.to_wallet_id))
    labels_by_wallet = await get_current_labels(session, list(wallet_ids))

    nodes = []
    for wallet_id in wallet_ids:
        wallet = await session.get(Wallet, wallet_id)
        nodes.append(
            {
                "wallet_id": str(wallet.id),
                "address": wallet.address,
                "chain": wallet.chain,
                "wallet_kind": wallet.wallet_kind.value if wallet.wallet_kind else None,
                "labels": [
                    {
                        "label": label.label,
                        "label_type": label.label_type.value,
                        "risk_color": label.risk_color.value if label.risk_color else None,
                        "data_ledger_id": label.data_ledger_id,
                        "observed_at": label.observed_at.isoformat(),
                    }
                    for label in labels_by_wallet.get(wallet.id, [])
                ],
            }
        )
    edges = [
        {
            "hop_id": str(hop.id),
            "hop_index": hop.hop_index,
            "from_wallet_id": str(hop.from_wallet_id),
            "to_wallet_id": str(hop.to_wallet_id),
            "tx_hash": hop.tx_hash,
            "asset": hop.asset,
            "amount": str(hop.amount),
            "confidence": str(hop.confidence),
            "boundary_flag": hop.boundary_flag.value if hop.boundary_flag else None,
        }
        for hop in confirmed
    ]
    return {"nodes": nodes, "edges": edges, "attribution_method": trace.attribution_method.value}
