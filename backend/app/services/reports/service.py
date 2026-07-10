"""Report service: draft, versions, approve.

Rules (02 Block H, LD-17): reports are drafts by default; versions are
immutable (new content = new version row); human review gates finalization —
approval is a human action and writes a decision_ledger event in the same
transaction (LD-9 pattern). freeze_blocklist_request and sar_draft are
legal-weight communications and always arrive as drafts.

Drafting goes through the task executor (single AI path, logged), never a
route-level prompt call.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.logging import get_logger, log_fields
from app.db.models import Report, ReportVersion
from app.db.models.enums import (
    DecisionLedgerEventType,
    LearningEventType,
    ReportStatus,
    ReportType,
)
from app.db.repositories.cases import get_case
from app.services.ai.task_executor import execute_case_task
from app.services.ledgers.learning import capture_learning_event
from app.services.ledgers.writers import write_decision_event
from app.services.reports.jurisdictions import jurisdiction_overlay
from app.services.reports.prompts import drafting_instructions

logger = get_logger(__name__)


async def draft_report(
    session: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    *,
    case_id: UUID,
    report_type: ReportType,
    title: str,
    jurisdiction: str | None,
    instructions: str | None,
) -> tuple[Report, ReportVersion]:
    """Create a report (status=draft) with its first AI-generated version."""
    case = await get_case(session, tenant_id, case_id)
    if case is None:
        raise NotFoundError("Case not found.")

    extra = drafting_instructions(report_type)
    overlay = jurisdiction_overlay(jurisdiction)
    if overlay:
        extra = f"{extra}\n\nJurisdiction variant ({jurisdiction}): {overlay}"
    if instructions:
        extra = f"{extra}\n\nInvestigator instructions: {instructions}"

    result = await execute_case_task(
        session,
        tenant_id=tenant_id,
        case_id=case_id,
        task_type="report_drafting",
        user_input=f"Draft a {report_type.value} titled {title!r}.",
        extra_instructions=extra,
    )

    report = Report(
        tenant_id=tenant_id,
        workspace_id=case.workspace_id,
        case_id=case_id,
        report_type=report_type,
        title=title,
        jurisdiction=jurisdiction,
        created_by=user_id,
    )
    session.add(report)
    await session.flush()
    version = ReportVersion(
        report_id=report.id,
        version_number=1,
        content_markdown=result.text,
        source_refs_json={"refs": result.source_refs},
        generated_by_ai=True,
        created_by=user_id,
    )
    session.add(version)
    await session.flush()
    report.current_version_id = version.id
    await session.commit()
    # updated_at is server-generated on UPDATE; load fresh values for the response.
    await session.refresh(report)
    logger.info(
        "report drafted",
        extra=log_fields(module="reports", action="draft", status="ok",
                         case_id=str(case_id)),
    )
    return report, version


async def get_report(session: AsyncSession, tenant_id: UUID, report_id: UUID) -> Report:
    result = await session.execute(
        select(Report).where(Report.id == report_id, Report.tenant_id == tenant_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise NotFoundError("Report not found.")
    return report


async def list_versions(
    session: AsyncSession, tenant_id: UUID, report_id: UUID
) -> list[ReportVersion]:
    await get_report(session, tenant_id, report_id)
    result = await session.execute(
        select(ReportVersion)
        .where(ReportVersion.report_id == report_id)
        .order_by(ReportVersion.version_number)
    )
    return list(result.scalars())


async def approve_report(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, report_id: UUID
) -> Report:
    """Human approval gate: draft/in_review → approved, plus a decision_ledger
    event in the same transaction."""
    report = await get_report(session, tenant_id, report_id)
    if report.status not in (ReportStatus.DRAFT, ReportStatus.IN_REVIEW):
        raise ConflictError(f"Report is already {report.status.value}.")

    report.status = ReportStatus.APPROVED
    await write_decision_event(
        session,
        tenant_id=tenant_id,
        workspace_id=report.workspace_id,
        case_id=report.case_id,
        decision_id=None,
        event_type=DecisionLedgerEventType.APPROVED,
        actor_id=user_id,
        actor_type="user",
        inputs_ref={"report_id": str(report.id),
                    "version_id": str(report.current_version_id)},
        approved=True,
    )
    # LD-30: consent-gated capture, same transaction as the approval.
    await capture_learning_event(
        session,
        tenant_id=tenant_id,
        workspace_id=report.workspace_id,
        case_id=report.case_id,
        actor_id=user_id,
        event_type=LearningEventType.DRAFT_APPROVED,
        subject_type="report",
        subject_id=str(report.id),
        payload={"report_type": report.report_type.value,
                 "version_id": str(report.current_version_id)},
    )
    await session.commit()
    await session.refresh(report)
    logger.info(
        "report approved",
        extra=log_fields(module="reports", action="approve", status="ok",
                         case_id=str(report.case_id)),
    )
    return report
