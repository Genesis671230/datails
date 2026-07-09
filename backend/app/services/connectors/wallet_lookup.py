"""Wallet lookup through a connector, with optional attach-to-case.

Vendor-agnostic: works for any connector type whose client supports the
wallet_lookup operation. The attach flow runs inside the LD-4 ledger
transaction via the execution service's side-effects hook, so wallet, case
link, and provenance labels (LD-14: data_ledger_id REQUIRED for
connector-sourced labels) commit atomically with the data_ledger entry.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models import CaseWallet, DataLedgerEntry, Wallet, WalletLabel
from app.db.models.enums import CaseWalletRole, ConnectorType, LabelSourceType
from app.db.repositories.cases import get_case, get_case_wallet_link, get_wallet_by_address
from app.integrations.generic_api.base import ConnectorResult
from app.schemas.connectors import WalletLookupAndAttachRequest, WalletLookupRequest
from app.services.connectors.execution import ExecutionOutcome, execute_connector_operation
from app.services.connectors.service import get_active_connector_by_type

OPERATION_WALLET_LOOKUP = "wallet_lookup"


async def wallet_lookup(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    connector_type: ConnectorType,
    data: WalletLookupRequest,
) -> ExecutionOutcome:
    """Look up a wallet; snapshot + ledger only (no wallet row is created)."""
    connector = await get_active_connector_by_type(session, tenant_id, connector_type)
    return await execute_connector_operation(
        session,
        connector,
        operation=OPERATION_WALLET_LOOKUP,
        params={"address": data.address, "chain": data.chain, "mode": data.mode},
        case_id=None,
        triggered_by_user_id=user_id,
    )


async def wallet_lookup_and_attach(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    connector_type: ConnectorType,
    data: WalletLookupAndAttachRequest,
) -> tuple[ExecutionOutcome, Wallet]:
    """Look up a wallet and attach it to a case with provenance labels.

    Wallet upsert (LD-13), case link, and wallet_labels rows join the LD-4
    ledger transaction — all or nothing.
    """
    case = await get_case(session, tenant_id, data.case_id)
    if case is None:
        raise NotFoundError("Case not found.")
    connector = await get_active_connector_by_type(session, tenant_id, connector_type)

    attached: dict[str, Wallet] = {}

    async def _attach(
        tx_session: AsyncSession, entry: DataLedgerEntry, result: ConnectorResult
    ) -> None:
        wallet = await get_wallet_by_address(
            tx_session, tenant_id, case.workspace_id, data.chain, data.address
        )
        if wallet is None:
            wallet = Wallet(
                tenant_id=tenant_id,
                workspace_id=case.workspace_id,
                address=data.address,
                chain=data.chain,
                first_seen_at=datetime.now(UTC),
            )
            tx_session.add(wallet)
            await tx_session.flush()

        link = await get_case_wallet_link(tx_session, tenant_id, data.case_id, wallet.id)
        if link is None:
            tx_session.add(
                CaseWallet(
                    case_id=data.case_id,
                    wallet_id=wallet.id,
                    tenant_id=tenant_id,
                    role_in_case=(
                        CaseWalletRole(data.role_in_case) if data.role_in_case else None
                    ),
                    added_by=user_id,
                )
            )

        observed_at = datetime.now(UTC)
        for label in result.labels:
            tx_session.add(
                WalletLabel(
                    wallet_id=wallet.id,
                    tenant_id=tenant_id,
                    label=label.label,
                    label_type=label.label_type,
                    risk_color=label.risk_color,
                    source_type=LabelSourceType.CONNECTOR,
                    connector_id=connector.id,
                    # LD-14: provenance link is REQUIRED for connector labels.
                    data_ledger_id=entry.id,
                    observed_at=observed_at,
                )
            )
        attached["wallet"] = wallet

    outcome = await execute_connector_operation(
        session,
        connector,
        operation=OPERATION_WALLET_LOOKUP,
        params={"address": data.address, "chain": data.chain, "mode": data.mode},
        case_id=data.case_id,
        triggered_by_user_id=user_id,
        side_effects=_attach,
    )
    return outcome, attached["wallet"]
