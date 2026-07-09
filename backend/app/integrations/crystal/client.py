"""Crystal connector (LD-16/LD-22).

ALL Crystal knowledge lives in this package: operations, Datails-side modes
(risk_check = fast Risk Check API; full_investigation = deep calls — Datails
product terms, no claim about Crystal's own API tiering), payload
normalization, and fixtures. Nothing outside integrations/crystal/ may import
from here except the connector registry (genericity criterion).

Transports:
- replay: serves recorded fixtures (dev/CI; currently synthetic pending LD-6)
- live: real API calls — BLOCKED until the LD-6 spike confirms auth, base
  URL, endpoint shapes, and licensing, and the shared temporary key exists
  in the secret store (LD-22).
"""

from decimal import Decimal

from app.core.config import get_settings
from app.db.models.enums import RiskColor, WalletLabelType
from app.integrations.crystal.fixtures import load_crystal_fixture
from app.integrations.generic_api.base import (
    ConnectorClient,
    ConnectorExecutionError,
    ConnectorResult,
    NormalizedLabel,
    NormalizedTransfer,
)

OPERATION_WALLET_LOOKUP = "wallet_lookup"
MODES = ("risk_check", "full_investigation")

# Crystal entity categories treated as risk flags rather than entity labels.
_RISK_FLAG_CATEGORIES = {"sanctions", "scam", "mixer", "darknet"}


class CrystalConnector(ConnectorClient):
    def needs_secret(self, operation: str) -> bool:
        return get_settings().crystal_transport == "live"

    async def execute(
        self, operation: str, params: dict, secret: str | None
    ) -> ConnectorResult:
        if operation != OPERATION_WALLET_LOOKUP:
            raise ConnectorExecutionError(f"crystal does not support operation {operation!r}")
        mode = params.get("mode", "risk_check")
        if mode not in MODES:
            raise ConnectorExecutionError(f"unknown crystal mode {mode!r}")

        settings = get_settings()
        if settings.crystal_transport == "replay":
            payload = load_crystal_fixture(mode)
            return self._normalize(payload, operation)
        return await self._execute_live(mode, params, secret)

    async def _execute_live(
        self, mode: str, params: dict, secret: str | None
    ) -> ConnectorResult:
        # Live transport is gated on the LD-6 spike: auth mechanism, base URL,
        # exact endpoints, payload shapes, and licensing must be confirmed
        # against the real API before this is implemented. Failing loudly here
        # is deliberate — no guessed endpoint shapes (master prompt: do not
        # invent; LD-6: contracts provisional until the spike).
        raise ConnectorExecutionError(
            "Crystal live transport is not implemented yet: it requires the "
            "LD-6 API spike (needs the temporary shared key, LD-22). "
            "Set CRYSTAL_TRANSPORT=replay for recorded fixtures."
        )

    def _normalize(self, payload: dict, operation: str) -> ConnectorResult:
        labels = [
            NormalizedLabel(
                label=entity["name"],
                label_type=(
                    WalletLabelType.RISK_FLAG
                    if entity.get("category") in _RISK_FLAG_CATEGORIES
                    else WalletLabelType.ENTITY
                ),
                risk_color=_risk_color(payload.get("risk_color")),
                confidence=(
                    Decimal(str(entity["confidence"]))
                    if entity.get("confidence") is not None
                    else None
                ),
            )
            for entity in payload.get("entities", [])
        ]
        transfers = [
            NormalizedTransfer(
                tx_hash=transfer["tx_hash"],
                direction=transfer["direction"],
                counterparty_address=transfer["counterparty_address"],
                asset=transfer["asset"],
                amount=str(transfer["amount"]),
                timestamp=transfer.get("timestamp"),
            )
            for transfer in payload.get("transfers", [])
        ]
        return ConnectorResult(
            raw_payload=payload,
            operation=operation,
            address=payload.get("address"),
            chain=payload.get("chain"),
            risk_score=payload.get("risk_score"),
            risk_color=_risk_color(payload.get("risk_color")),
            labels=labels,
            transfers=transfers,
            source_ref=f"crystal:{payload.get('mode', 'unknown')}",
        )


def _risk_color(value: str | None) -> RiskColor | None:
    return RiskColor(value) if value else None
