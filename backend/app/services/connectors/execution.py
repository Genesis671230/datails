"""Connector execution service — the LD-4 ingestion pipeline.

Canonical sequence for every durable connector run:
1. enforce limits (per-connector daily limit derived from connector_runs,
   LD-11; global shared-key budget, LD-22),
2. resolve secret from the secret store (only if the client needs one),
3. execute the external call,
4. write the raw payload to blob storage; compute SHA-256,
5. in ONE database transaction: write the data_ledger entry, mark the
   connector_run completed, and apply any caller side effects (e.g. wallet
   labels with provenance).

Failure semantics (LD-4): external call fails → run failed, no blob, no
ledger. Blob write fails → run failed, no ledger. Ledger transaction fails →
run failed; an orphaned blob is tolerable, a ledger entry pointing at nothing
is not.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import LimitExceededError, UpstreamError
from app.core.hashing import canonical_json_bytes, sha256_hex
from app.core.logging import get_logger, log_fields
from app.db.models import Connector, ConnectorRun, DataLedgerEntry
from app.db.models.enums import ConnectorRunStatus, CredentialOwner
from app.integrations.factories import get_blob_storage, get_secret_resolver
from app.integrations.generic_api.base import ConnectorExecutionError, ConnectorResult
from app.integrations.key_vault.base import SecretResolutionError
from app.integrations.registry import get_connector_client
from app.services.ledgers.writers import write_data_ledger_entry

logger = get_logger(__name__)

SNAPSHOT_CONTAINER = "snapshots"

# Applied inside the ledger transaction, before commit. Receives the session,
# the data_ledger entry, and the normalized result.
SideEffects = Callable[[AsyncSession, DataLedgerEntry, ConnectorResult], Awaitable[None]]


@dataclass(frozen=True)
class ExecutionOutcome:
    run: ConnectorRun
    ledger_entry: DataLedgerEntry
    result: ConnectorResult


async def _runs_today(session: AsyncSession, *, connector_id: UUID | None = None,
                      shared_type=None) -> int:
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(func.count(ConnectorRun.id)).where(ConnectorRun.started_at >= start_of_day)
    if connector_id is not None:
        query = query.where(ConnectorRun.connector_id == connector_id)
    if shared_type is not None:
        query = query.join(Connector, ConnectorRun.connector_id == Connector.id).where(
            Connector.connector_type == shared_type,
            Connector.credential_owner == CredentialOwner.DATAILS_SHARED,
        )
    return (await session.execute(query)).scalar_one()


async def _enforce_limits(session: AsyncSession, connector: Connector) -> None:
    if connector.daily_call_limit is not None:
        used = await _runs_today(session, connector_id=connector.id)
        if used >= connector.daily_call_limit:
            raise LimitExceededError(
                f"daily call limit ({connector.daily_call_limit}) reached for this connector"
            )
    # Shared-key arbitration (LD-22): one cohort member must not starve the
    # others. Counted across ALL tenants using the shared credential.
    if connector.credential_owner == CredentialOwner.DATAILS_SHARED:
        budget = get_settings().shared_key_daily_budget
        used_globally = await _runs_today(session, shared_type=connector.connector_type)
        if used_globally >= budget:
            raise LimitExceededError(
                "global daily budget for the shared key is exhausted; try tomorrow"
            )


async def execute_connector_operation(
    session: AsyncSession,
    connector: Connector,
    *,
    operation: str,
    params: dict,
    case_id: UUID | None,
    triggered_by_user_id: UUID | None,
    side_effects: SideEffects | None = None,
) -> ExecutionOutcome:
    """Run one connector operation through the full LD-4 pipeline."""
    client = get_connector_client(connector.connector_type)
    await _enforce_limits(session, connector)

    run = ConnectorRun(
        connector_id=connector.id,
        tenant_id=connector.tenant_id,
        workspace_id=connector.workspace_id,
        triggered_by_user_id=triggered_by_user_id,
        status=ConnectorRunStatus.RUNNING,
        request_ref=f"{operation}:{params.get('address', '')}",
    )
    session.add(run)
    await session.commit()

    async def _fail(message: str) -> None:
        run.status = ConnectorRunStatus.FAILED
        run.error_message = message
        run.completed_at = datetime.now(UTC)
        await session.commit()

    # 1–3: secret + external call. Failure → run failed, no blob, no ledger.
    try:
        secret = None
        if client.needs_secret(operation):
            if not connector.secret_ref:
                raise SecretResolutionError("connector has no secret_ref configured")
            secret = await get_secret_resolver().get_secret(connector.secret_ref)
        result = await client.execute(operation, params, secret)
    except (ConnectorExecutionError, SecretResolutionError) as exc:
        await _fail(str(exc))
        logger.info(
            "connector run failed upstream: %s",
            exc,
            extra=log_fields(module="connectors", action=operation, status="failed"),
        )
        raise UpstreamError(f"Connector call failed: {exc}") from exc

    # 4: blob snapshot. Failure → run failed, no ledger.
    payload_bytes = canonical_json_bytes(result.raw_payload)
    payload_hash = sha256_hex(payload_bytes)
    blob_name = f"{connector.tenant_id}/{connector.id}/{run.id}.json"
    try:
        storage_ref = await get_blob_storage().put(
            SNAPSHOT_CONTAINER, blob_name, payload_bytes
        )
    except Exception as exc:
        await _fail(f"blob write failed: {exc}")
        raise UpstreamError("Snapshot storage failed; run recorded as failed.") from exc

    # 5: one transaction — ledger entry + run completion + caller side effects.
    # Failure → run failed; the orphaned blob is tolerable (LD-4).
    try:
        entry = await write_data_ledger_entry(
            session,
            tenant_id=connector.tenant_id,
            workspace_id=connector.workspace_id,
            case_id=case_id,
            connector_id=connector.id,
            source_type="connector",
            source_ref=result.source_ref,
            payload_hash=payload_hash,
            storage_ref=storage_ref,
            retrieved_by_user_id=triggered_by_user_id,
        )
        run.status = ConnectorRunStatus.COMPLETED
        run.response_ref = storage_ref
        run.completed_at = datetime.now(UTC)
        if side_effects is not None:
            await side_effects(session, entry, result)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        await _fail(f"ledger transaction failed: {exc}")
        raise UpstreamError("Provenance write failed; run recorded as failed.") from exc

    logger.info(
        "connector run completed",
        extra=log_fields(
            module="connectors",
            action=operation,
            status="ok",
            case_id=str(case_id) if case_id else None,
        ),
    )
    return ExecutionOutcome(run=run, ledger_entry=entry, result=result)
