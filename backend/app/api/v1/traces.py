"""Trace routes (05 §8): create, get (with explorer graph), confirm, reject.

Thin handlers; the trace service owns the loop, the state machine (LD-27),
and the ledger writes.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import AuthContext, DbSession, get_auth_context
from app.schemas.traces import TraceCreateRequest, TraceDetailOut, TraceHopOut, TraceOut
from app.services.traces import service as traces_service

router = APIRouter()

Ctx = Annotated[AuthContext, Depends(get_auth_context)]


async def _detail(session, tenant_id, trace_id) -> TraceDetailOut:
    trace, run, hops = await traces_service.get_trace_state(session, tenant_id, trace_id)
    graph = await traces_service.build_graph(session, tenant_id, trace_id)
    base = TraceOut.model_validate(trace)
    return TraceDetailOut(
        **base.model_dump(),
        hops=[TraceHopOut.model_validate(h) for h in hops],
        run_output=run.output_ref_json,
        graph=graph,
    )


@router.post("/cases/{case_id}/traces", response_model=TraceDetailOut, status_code=201)
async def create_trace(
    case_id: UUID, body: TraceCreateRequest, ctx: Ctx, session: DbSession
) -> TraceDetailOut:
    trace = await traces_service.create_trace(
        session, ctx.tenant_id, ctx.user.id,
        case_id=case_id, root_wallet_id=body.root_wallet_id,
    )
    return await _detail(session, ctx.tenant_id, trace.id)


@router.get("/traces/{trace_id}", response_model=TraceDetailOut)
async def get_trace(trace_id: UUID, ctx: Ctx, session: DbSession) -> TraceDetailOut:
    return await _detail(session, ctx.tenant_id, trace_id)


@router.post("/traces/{trace_id}/hops/{hop_id}/confirm", response_model=TraceDetailOut)
async def confirm_hop(
    trace_id: UUID, hop_id: UUID, ctx: Ctx, session: DbSession
) -> TraceDetailOut:
    await traces_service.confirm_hop(session, ctx.tenant_id, ctx.user.id, trace_id, hop_id)
    return await _detail(session, ctx.tenant_id, trace_id)


@router.post("/traces/{trace_id}/hops/{hop_id}/reject", response_model=TraceDetailOut)
async def reject_hop(
    trace_id: UUID, hop_id: UUID, ctx: Ctx, session: DbSession
) -> TraceDetailOut:
    await traces_service.reject_hop(session, ctx.tenant_id, ctx.user.id, trace_id, hop_id)
    return await _detail(session, ctx.tenant_id, trace_id)
