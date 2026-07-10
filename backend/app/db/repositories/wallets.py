"""Wallet-label queries.

"Current" labels under the append-only model (LD-14): the latest observation
per (wallet, label) by observed_at — older rows are history, never deleted.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WalletLabel


async def get_current_labels(
    session: AsyncSession, wallet_ids: list[UUID]
) -> dict[UUID, list[WalletLabel]]:
    if not wallet_ids:
        return {}
    rows = (
        (
            await session.execute(
                select(WalletLabel)
                .where(WalletLabel.wallet_id.in_(wallet_ids))
                .order_by(WalletLabel.observed_at.desc())
            )
        )
        .scalars()
        .all()
    )
    latest: dict[tuple[UUID, str], WalletLabel] = {}
    for row in rows:
        latest.setdefault((row.wallet_id, row.label), row)
    grouped: dict[UUID, list[WalletLabel]] = {}
    for label in latest.values():
        grouped.setdefault(label.wallet_id, []).append(label)
    return grouped
