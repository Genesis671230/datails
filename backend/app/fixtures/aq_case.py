"""AQ case fixture loader.

Loads the anonymised AQ case (currently a clearly-marked PLACEHOLDER, see
aq_case_placeholder.json) into a workspace: case + workspace-global wallets
(LD-13) + case_wallet links. Expected hops are returned for tests and the
later golden-set/demo script — traces themselves are Slice 3 work.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Case, CaseWallet, Tenant, User, Wallet, Workspace
from app.db.models.enums import CasePriority, CaseType, CaseWalletRole, WalletKind

FIXTURE_PATH = Path(__file__).parent / "aq_case_placeholder.json"


@dataclass(frozen=True)
class LoadedAqCase:
    case: Case
    wallets: dict[str, Wallet]  # fixture ref -> wallet
    expected_hops: list[dict]
    is_placeholder: bool


def read_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


async def load_aq_case(
    session: AsyncSession, tenant: Tenant, workspace: Workspace, user: User
) -> LoadedAqCase:
    """Create the fixture case and its wallets in the given workspace.

    Flushes but does not commit — the caller owns the transaction.
    """
    data = read_fixture()

    case_data = data["case"]
    case = Case(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        created_by=user.id,
        title=case_data["title"],
        case_type=CaseType(case_data["case_type"]),
        priority=CasePriority(case_data["priority"]),
        summary=case_data["summary"],
        metadata_json=case_data["metadata"],
    )
    session.add(case)
    await session.flush()

    wallets: dict[str, Wallet] = {}
    for wallet_data in data["wallets"]:
        wallet = Wallet(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            address=wallet_data["address"],
            chain=wallet_data["chain"],
            wallet_kind=WalletKind(wallet_data["wallet_kind"]),
        )
        session.add(wallet)
        await session.flush()
        session.add(
            CaseWallet(
                case_id=case.id,
                wallet_id=wallet.id,
                tenant_id=tenant.id,
                role_in_case=CaseWalletRole(wallet_data["role_in_case"]),
                added_by=user.id,
            )
        )
        wallets[wallet_data["ref"]] = wallet
    await session.flush()

    return LoadedAqCase(
        case=case,
        wallets=wallets,
        expected_hops=data["expected_hops"],
        is_placeholder=bool(data.get("_placeholder", False)),
    )
