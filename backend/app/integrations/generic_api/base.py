"""Generic connector contracts (Block C).

Every vendor connector implements ConnectorClient and returns a
ConnectorResult in the SAME normalized shape — services never see vendor
payloads or vendor modules. Adding a vendor means one new
integrations/<name>/ module plus a registry entry; zero service or schema
changes (Slice 1 connector-genericity criterion; LD-19 names generic_api as
the base-class/mock home).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from app.db.models.enums import RiskColor, WalletLabelType


class ConnectorExecutionError(Exception):
    """External call failed (network, vendor error, unsupported operation).
    Message must be safe to store in connector_runs.error_message."""


@dataclass(frozen=True)
class NormalizedLabel:
    """Vendor-agnostic wallet label observation (LD-14 provenance is added by
    the service when it writes wallet_labels)."""

    label: str
    label_type: WalletLabelType
    risk_color: RiskColor | None = None
    confidence: Decimal | None = None


@dataclass(frozen=True)
class NormalizedTransfer:
    tx_hash: str
    direction: str  # "in" | "out"
    counterparty_address: str
    asset: str
    amount: str
    timestamp: str | None = None


@dataclass(frozen=True)
class ConnectorResult:
    """What every connector execution returns to the service layer."""

    raw_payload: dict
    operation: str
    address: str | None = None
    chain: str | None = None
    risk_score: float | None = None
    risk_color: RiskColor | None = None
    labels: list[NormalizedLabel] = field(default_factory=list)
    transfers: list[NormalizedTransfer] = field(default_factory=list)
    source_ref: str | None = None


class ConnectorClient(ABC):
    """One instance per connector type, stateless. Secrets are passed per
    call and never stored."""

    @abstractmethod
    def needs_secret(self, operation: str) -> bool:
        """Whether execute() requires a resolved secret for this operation."""

    @abstractmethod
    async def execute(
        self, operation: str, params: dict, secret: str | None
    ) -> ConnectorResult:
        """Run one operation against the vendor; raise ConnectorExecutionError
        on failure."""


class MockConnector(ConnectorClient):
    """The generic_api mock (LD-19): echoes configured params. Used by tests
    to exercise the execution pipeline without any vendor."""

    def needs_secret(self, operation: str) -> bool:
        return False

    async def execute(
        self, operation: str, params: dict, secret: str | None
    ) -> ConnectorResult:
        if params.get("simulate_failure"):
            raise ConnectorExecutionError("mock connector simulated failure")
        return ConnectorResult(
            raw_payload={"operation": operation, "params": params, "mock": True},
            operation=operation,
            address=params.get("address"),
            chain=params.get("chain"),
            source_ref="mock://generic-api",
        )
