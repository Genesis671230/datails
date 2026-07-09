"""Ledger writer services (Blocks E/F).

Writers add rows to the current session WITHOUT committing: the caller owns
the transaction. That is the LD-9/LD-4 mechanism — a decision write and its
ledger event (or a snapshot and its data_ledger entry) commit or roll back
together. Never commit inside a writer.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataLedgerEntry, DecisionLedgerEvent
from app.db.models.enums import DecisionLedgerEventType


async def write_decision_event(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    case_id: UUID,
    decision_id: UUID | None,
    event_type: DecisionLedgerEventType,
    actor_id: UUID | None,
    actor_type: str,
    inputs_ref: dict | None = None,
    approved: bool | None = None,
) -> DecisionLedgerEvent:
    event = DecisionLedgerEvent(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        case_id=case_id,
        decision_id=decision_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_type=actor_type,
        inputs_ref_json=inputs_ref,
        approved=approved,
    )
    session.add(event)
    await session.flush()
    return event


async def write_data_ledger_entry(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    case_id: UUID | None,
    connector_id: UUID | None,
    source_type: str,
    source_ref: str | None,
    payload_hash: str,
    storage_ref: str,
    retrieved_by_user_id: UUID | None,
) -> DataLedgerEntry:
    entry = DataLedgerEntry(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        case_id=case_id,
        connector_id=connector_id,
        source_type=source_type,
        source_ref=source_ref,
        payload_hash=payload_hash,
        storage_ref=storage_ref,
        retrieved_by_user_id=retrieved_by_user_id,
    )
    session.add(entry)
    await session.flush()
    return entry
