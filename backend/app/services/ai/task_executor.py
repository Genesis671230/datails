"""AI task executor — the single path for every model call (02 Block G).

Responsibilities: build scoped context (LD-5), route to a model (LD-24),
execute through the model-client interface, and log EVERY call — success or
failure — to ai_call_log (01 §9). No route or service may call a model
client directly.

Prompt templates live in prompts.py, not inline strings (02 AI rule 1).
"""

import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, UpstreamError
from app.core.hashing import sha256_hex
from app.core.logging import get_logger, log_fields
from app.db.models import AiCallLogEntry
from app.db.repositories.cases import get_case
from app.integrations.azure_foundry.base import ModelClientError
from app.integrations.factories import get_model_client
from app.services.ai.context_builder import CaseContext, build_case_context
from app.services.ai.model_router import get_route
from app.services.ai.prompts import build_prompt, system_prompt_for

logger = get_logger(__name__)

STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class AiTaskResult:
    text: str
    model: str
    source_refs: list[str]
    ai_call_log_id: int
    token_input: int | None
    token_output: int | None


async def execute_case_task(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    case_id: UUID,
    task_type: str,
    user_input: str,
    workflow_agent_id: UUID | None = None,
    extra_instructions: str | None = None,
) -> AiTaskResult:
    """Run one case-grounded AI task through context builder → router →
    model client, logging to ai_call_log either way."""
    case = await get_case(session, tenant_id, case_id)
    if case is None:
        raise NotFoundError("Case not found.")

    route = get_route(task_type)
    context: CaseContext = await build_case_context(session, tenant_id, case_id, task_type)
    system = system_prompt_for(task_type)
    prompt = build_prompt(
        task_type=task_type,
        context_text=context.text,
        source_refs=context.source_refs,
        user_input=user_input,
        extra_instructions=extra_instructions,
    )
    prompt_hash = sha256_hex(prompt.encode())

    started = time.monotonic()
    try:
        response = await get_model_client().complete(
            model=route.model, system=system, prompt=prompt
        )
    except ModelClientError as exc:
        await _log_call(
            session,
            case=case,
            workflow_agent_id=workflow_agent_id,
            task_type=task_type,
            model_name=route.model,
            prompt_hash=prompt_hash,
            response_hash=None,
            token_input=None,
            token_output=None,
            latency_ms=int((time.monotonic() - started) * 1000),
            status=STATUS_FAILED,
        )
        logger.info(
            "ai task failed: %s",
            exc,
            extra=log_fields(module="ai", action=task_type, status="failed",
                             case_id=str(case_id)),
        )
        raise UpstreamError(f"AI task failed: {exc}") from exc

    entry = await _log_call(
        session,
        case=case,
        workflow_agent_id=workflow_agent_id,
        task_type=task_type,
        model_name=response.model,
        prompt_hash=prompt_hash,
        response_hash=sha256_hex(response.text.encode()),
        token_input=response.token_input,
        token_output=response.token_output,
        latency_ms=int((time.monotonic() - started) * 1000),
        status=STATUS_COMPLETED,
    )
    return AiTaskResult(
        text=response.text,
        model=response.model,
        source_refs=context.source_refs,
        ai_call_log_id=entry.id,
        token_input=response.token_input,
        token_output=response.token_output,
    )


async def _log_call(session: AsyncSession, *, case, workflow_agent_id, task_type,
                    model_name, prompt_hash, response_hash, token_input, token_output,
                    latency_ms, status) -> AiCallLogEntry:
    entry = AiCallLogEntry(
        tenant_id=case.tenant_id,
        workspace_id=case.workspace_id,
        case_id=case.id,
        workflow_agent_id=workflow_agent_id,
        task_type=task_type,
        model_name=model_name,
        prompt_hash=prompt_hash,
        response_hash=response_hash,
        token_input=token_input,
        token_output=token_output,
        latency_ms=latency_ms,
        status=status,
    )
    session.add(entry)
    await session.commit()
    return entry
