"""LD-3 acceptance: ledger tables reject UPDATE/DELETE at the database level.

Two mechanisms, both tested:
- grants: the application role lacks UPDATE/DELETE on the four ledger tables,
- triggers: even the owner role is rejected (defense in depth).
Positive path (INSERT + SELECT as the application role) is covered too.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.db.models import (
    AiCallLogEntry,
    DataLedgerEntry,
    DecisionLedgerEvent,
    LearningEvent,
)
from app.db.models.enums import DecisionLedgerEventType, LearningEventType
from app.tests.factories import create_tenant_chain

FAKE_HASH = "0" * 64


async def _insert_ledger_rows(session) -> dict[str, int]:
    """Insert one row per ledger table; return table -> id."""
    tenant, user, workspace, case = await create_tenant_chain(session)

    data_entry = DataLedgerEntry(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        case_id=case.id,
        source_type="connector",
        payload_hash=FAKE_HASH,
        storage_ref="local://test/payload.json",
        retrieved_by_user_id=user.id,
    )
    decision_event = DecisionLedgerEvent(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        case_id=case.id,
        event_type=DecisionLedgerEventType.CREATED,
        actor_id=user.id,
        actor_type="user",
    )
    ai_entry = AiCallLogEntry(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        case_id=case.id,
        task_type="test",
        model_name="none",
        prompt_hash=FAKE_HASH,
        status="completed",
    )
    learning_event = LearningEvent(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        case_id=case.id,
        actor_id=user.id,
        event_type=LearningEventType.DRAFT_APPROVED,
        subject_type="report",
        subject_id="test",
    )
    session.add_all([data_entry, decision_event, ai_entry, learning_event])
    await session.commit()
    return {
        "data_ledger": data_entry.id,
        "decision_ledger": decision_event.id,
        "ai_call_log": ai_entry.id,
        "learning_events": learning_event.id,
    }


async def test_app_role_can_insert_and_select_ledgers(app_session) -> None:
    ids = await _insert_ledger_rows(app_session)
    for table, row_id in ids.items():
        result = await app_session.execute(
            text(f"SELECT count(*) FROM {table} WHERE id = :id"), {"id": row_id}
        )
        assert result.scalar() == 1


@pytest.mark.parametrize("statement", ["UPDATE {t} SET created_at = now() WHERE id = :id",
                                       "DELETE FROM {t} WHERE id = :id"])
async def test_app_role_cannot_mutate_ledgers(app_session, statement) -> None:
    ids = await _insert_ledger_rows(app_session)
    for table, row_id in ids.items():
        with pytest.raises(ProgrammingError, match="permission denied"):
            await app_session.execute(text(statement.format(t=table)), {"id": row_id})
        await app_session.rollback()


@pytest.mark.parametrize("statement", ["UPDATE {t} SET created_at = now() WHERE id = :id",
                                       "DELETE FROM {t} WHERE id = :id"])
async def test_owner_role_blocked_by_trigger(app_session, owner_session, statement) -> None:
    ids = await _insert_ledger_rows(app_session)
    for table, row_id in ids.items():
        with pytest.raises(DBAPIError, match="append-only"):
            await owner_session.execute(text(statement.format(t=table)), {"id": row_id})
        await owner_session.rollback()
