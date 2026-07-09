"""Wallet models: wallets, case_wallets, wallet_labels.

Wallets are workspace-global (LD-13): criminal organizations reuse wallet
infrastructure across cases, so cases reference wallets through a join table.
Labels carry provenance (LD-14): no bare strings — every label knows its
source, connector, data_ledger reference, and observation time. Labels are
append-only in practice; "current" = latest by observed_at.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    CaseWalletRole,
    LabelSourceType,
    RiskColor,
    WalletKind,
    WalletLabelType,
)


def _enum(enum_cls, name: str):
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "chain", "address", name="uq_wallets_workspace_chain_address"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    address: Mapped[str] = mapped_column(String(255), index=True)
    chain: Mapped[str] = mapped_column(String(50))
    wallet_kind: Mapped[WalletKind | None] = mapped_column(_enum(WalletKind, "wallet_kind"))
    # Schema hook for dormant-wallet monitoring; no behavior in Phase 1 (LD-13).
    is_watched: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CaseWallet(Base):
    __tablename__ = "case_wallets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"), index=True)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    role_in_case: Mapped[CaseWalletRole | None] = mapped_column(
        _enum(CaseWalletRole, "case_wallet_role")
    )
    added_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WalletLabel(Base):
    __tablename__ = "wallet_labels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    label: Mapped[str] = mapped_column(String(500))
    label_type: Mapped[WalletLabelType] = mapped_column(_enum(WalletLabelType, "label_type"))
    risk_color: Mapped[RiskColor | None] = mapped_column(_enum(RiskColor, "risk_color"))
    source_type: Mapped[LabelSourceType] = mapped_column(
        _enum(LabelSourceType, "label_source_type")
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("connectors.id"))
    # Provenance link — REQUIRED when source_type = connector (LD-14). FK ships
    # in the single Slice-0 migration (LD-18.4 phasing collapses: ledgers exist
    # from day one).
    data_ledger_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("data_ledger.id")
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
