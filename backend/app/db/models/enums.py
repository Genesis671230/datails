"""Domain enums, all persisted as PostgreSQL enum types (07 Slice 0).

Values come verbatim from 05_DOMAIN_MODEL.md §1.3 (evidence-backed) and
§1.3a (pilot defaults), plus the locked decisions that name them
(LD-19, LD-21, LD-22, LD-27, LD-30). Do not "improve" these from general
knowledge — they were validated with operators.
"""

from enum import Enum


class UserRole(str, Enum):
    """Minimal Phase 1 roles (02 Block A)."""

    OWNER = "owner"
    INVESTIGATOR = "investigator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class OnboardingStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CaseType(str, Enum):
    """Six verticals, all starting from a transaction or wallet ID (05 §1.3)."""

    CRIMINAL_INVESTIGATION = "criminal_investigation"
    PROOF_OF_SOURCE_OF_FUNDS = "proof_of_source_of_funds"
    DIGITAL_INHERITANCE = "digital_inheritance"
    DIVORCE = "divorce"
    BANKRUPTCY = "bankruptcy"
    TAX_RECONSTRUCTION = "tax_reconstruction"


class CaseStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    CLOSED = "closed"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class EvidenceType(str, Enum):
    TRANSACTION_HISTORY_EXPORT = "transaction_history_export"
    SCREENSHOT = "screenshot"
    COMMUNICATION_RECORD = "communication_record"
    EXCHANGE_CORRESPONDENCE = "exchange_correspondence"
    POLICE_FILE_REFERENCE = "police_file_reference"
    ON_CHAIN_SNAPSHOT = "on_chain_snapshot"
    OTHER = "other"


class FindingType(str, Enum):
    WALLET_ATTRIBUTION = "wallet_attribution"
    TRANSACTION_TRACE = "transaction_trace"
    ENTITY_IDENTIFICATION = "entity_identification"
    EVIDENCE_SUMMARY = "evidence_summary"
    RISK_ASSESSMENT = "risk_assessment"
    OTHER = "other"


class DecisionType(str, Enum):
    OPEN_CASE = "open_case"
    FREEZE_REQUEST_SENT = "freeze_request_sent"
    REPORT_FILED = "report_filed"
    SAR_FILED = "sar_filed"
    CASE_CLOSED = "case_closed"
    ESCALATION = "escalation"
    OTHER = "other"


class WalletKind(str, Enum):
    HOT_WALLET = "hot_wallet"
    SELF_HOSTED = "self_hosted"
    COLD_STORAGE = "cold_storage"
    SMART_CONTRACT = "smart_contract"
    UNKNOWN = "unknown"


class CaseWalletRole(str, Enum):
    VICTIM = "victim"
    SUSPECT = "suspect"
    INTERMEDIARY = "intermediary"
    EXCHANGE_DEPOSIT = "exchange_deposit"
    UNKNOWN = "unknown"


class WalletLabelType(str, Enum):
    ENTITY = "entity"
    RISK_FLAG = "risk_flag"
    SCAM_REFERENCE = "scam_reference"
    USER_NOTE = "user_note"


class RiskColor(str, Enum):
    """Regulated / unregulated / sanctioned convention (05 §1.2)."""

    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class LabelSourceType(str, Enum):
    CONNECTOR = "connector"
    USER = "user"
    IMPORT = "import"


class ConnectorType(str, Enum):
    """Registrable Phase 1 types: crystal, blockchain_explorer, file_upload.

    generic_api is the base-class/mock type only (LD-19); mcp_server is
    reserved for future BYO connectors, not built in the pilot (LD-22).
    """

    CRYSTAL = "crystal"
    BLOCKCHAIN_EXPLORER = "blockchain_explorer"
    FILE_UPLOAD = "file_upload"
    GENERIC_API = "generic_api"
    MCP_SERVER = "mcp_server"


class ConnectorStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class ConnectorRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CredentialOwner(str, Enum):
    """LD-22: pilot Crystal key is Datails-shared; BYO supported from day one."""

    DATAILS_SHARED = "datails_shared"
    TENANT = "tenant"


class RunStatus(str, Enum):
    """Workflow-agent run and trace state machine (LD-27)."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class AgentType(str, Enum):
    INTAKE_ANALYST = "intake_analyst"
    REPORT_WRITER = "report_writer"
    COMPLIANCE_ANALYST = "compliance_analyst"
    RESEARCH_ANALYST = "research_analyst"


class AttributionMethod(str, Enum):
    """Trace attribution: FIFO in the pilot; alternatives are config (05 §8)."""

    FIFO = "fifo"
    LIFO = "lifo"
    PRO_RATA = "pro_rata"


class TraceHopStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class BoundaryFlag(str, Enum):
    """Human-judgment trace boundaries from operator evidence (05 §8)."""

    HOT_WALLET = "hot_wallet"
    MIXER = "mixer"
    CHAIN_HOP = "chain_hop"
    INTERNAL_LEDGER = "internal_ledger"


class DecisionLedgerEventType(str, Enum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"


class LearningEventType(str, Enum):
    """Learning Layer capture vocabulary (05 §9, LD-30)."""

    RECOMMENDATION_ACCEPTED = "recommendation_accepted"
    RECOMMENDATION_REJECTED = "recommendation_rejected"
    REPORT_EDITED = "report_edited"
    DRAFT_APPROVED = "draft_approved"
    DRAFT_REJECTED = "draft_rejected"
    OVERRIDE = "override"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ABANDONED = "workflow_abandoned"
    CONNECTOR_USED = "connector_used"
    TRACE_HOP_CONFIRMED = "trace_hop_confirmed"
    TRACE_HOP_REJECTED = "trace_hop_rejected"
    SESSION_DURATION = "session_duration"


class UsageCategory(str, Enum):
    AI_TASK = "ai_task"
    CONNECTOR_RUN = "connector_run"
    REPORT_GENERATION = "report_generation"
    STORAGE = "storage"
