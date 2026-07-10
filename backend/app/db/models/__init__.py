"""Model registry — import every model module so Base.metadata is complete.

Alembic autogenerate and test fixtures rely on this module importing the full
schema. Add new model modules here when a slice introduces them.
"""

from app.db.models.agents import WorkflowAgent, WorkflowAgentRun
from app.db.models.cases import Case, Decision, EvidenceItem, Finding
from app.db.models.connectors import Connector, ConnectorRun
from app.db.models.ledgers import (
    APPEND_ONLY_TABLES,
    AiCallLogEntry,
    DataLedgerEntry,
    DecisionLedgerEvent,
    LearningEvent,
)
from app.db.models.methodology import (
    GeneratedTemplate,
    Methodology,
    MethodologyStep,
    WorkflowAgentProfile,
)
from app.db.models.reports import Report, ReportVersion
from app.db.models.tenancy import OnboardingSession, Tenant, User, Workspace
from app.db.models.traces import Trace, TraceHop
from app.db.models.usage import IdempotencyKey, TenantPlanState, UsageRecord
from app.db.models.wallets import CaseWallet, Wallet, WalletLabel

__all__ = [
    "APPEND_ONLY_TABLES",
    "AiCallLogEntry",
    "Case",
    "CaseWallet",
    "Connector",
    "ConnectorRun",
    "DataLedgerEntry",
    "Decision",
    "DecisionLedgerEvent",
    "EvidenceItem",
    "Finding",
    "GeneratedTemplate",
    "IdempotencyKey",
    "LearningEvent",
    "Methodology",
    "MethodologyStep",
    "OnboardingSession",
    "Report",
    "ReportVersion",
    "Tenant",
    "TenantPlanState",
    "Trace",
    "TraceHop",
    "UsageRecord",
    "User",
    "Wallet",
    "WalletLabel",
    "Workspace",
    "WorkflowAgent",
    "WorkflowAgentProfile",
    "WorkflowAgentRun",
]
