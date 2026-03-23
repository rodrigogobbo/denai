"""Agent loop routes — start, approve, abort, status."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..agent import (
    PlanStatus,
    clear_plan,
    decompose_goal,
    execute_plan,
    get_current_plan,
    request_interrupt,
)
from ..config import DEFAULT_MODEL
from ..logging_config import get_logger

log = get_logger("routes.agent")

router = APIRouter()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# ─── Request Models ──────────────────────────────────────────────────────


class AgentGoalRequest(BaseModel):
    """Request body for agent start/approve endpoints."""

    goal: str = Field(..., min_length=1, description="The goal to decompose into a plan")
    model: str = Field(default=DEFAULT_MODEL, description="LLM model to use")


# ─── Routes ──────────────────────────────────────────────────────────────


@router.post("/api/agent/start")
async def agent_start(body: AgentGoalRequest):
    """Decompose a goal into an execution plan."""
    current = get_current_plan()
    if current and current.status in (PlanStatus.EXECUTING, PlanStatus.APPROVED):
        return JSONResponse(
            {"error": "A plan is already in progress. Abort it first."},
            status_code=409,
        )

    try:
        plan = await decompose_goal(body.goal.strip(), body.model)
        return {"ok": True, "plan": plan.to_dict()}
    except Exception:
        log.exception("Failed to decompose goal")
        return JSONResponse(
            {"error": "Failed to decompose goal. Check logs for details."},
            status_code=500,
        )


@router.post("/api/agent/approve")
async def agent_approve(body: AgentGoalRequest):
    """Approve and execute a plan. Streams progress via SSE.

    Reuses the current plan from /start if the goal matches,
    otherwise decomposes a new plan.
    """
    current = get_current_plan()

    if current and current.goal == body.goal.strip() and current.status == PlanStatus.DRAFT:
        # Reuse existing plan from /start instead of re-decomposing
        plan = current
    else:
        try:
            plan = await decompose_goal(body.goal.strip(), body.model)
        except Exception:
            log.exception("Failed to decompose goal for approval")
            return JSONResponse(
                {"error": "Failed to decompose goal. Check logs for details."},
                status_code=500,
            )

    plan.status = PlanStatus.APPROVED

    async def generate():
        try:
            async for event in execute_plan(plan):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:
            log.exception("Error during plan execution stream")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Execution failed. Check logs.'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/api/agent/abort")
async def agent_abort():
    """Abort the current plan."""
    current = get_current_plan()
    if not current:
        return JSONResponse({"error": "No active plan to abort"}, status_code=404)

    request_interrupt()
    current.status = PlanStatus.ABORTED
    result = current.to_dict()
    clear_plan()
    return {"ok": True, "plan": result}


@router.get("/api/agent/status")
async def agent_status():
    """Return current plan status."""
    current = get_current_plan()
    if not current:
        return {"active": False, "plan": None}
    return {"active": True, "plan": current.to_dict()}
