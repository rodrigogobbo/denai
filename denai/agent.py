"""Agent loop — autonomous multi-step execution with checkpoints."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .logging_config import get_logger
from .permissions import check_permission
from .undo import save_snapshot, start_changeset

log = get_logger("agent")

# ─── Constants ───────────────────────────────────────────────────────────

MAX_TOOL_CALLS = 50
_RESULT_TRUNCATE_LIMIT = 500
_GOAL_LABEL_LIMIT = 50

# Tools that modify state (require undo snapshots)
_DESTRUCTIVE_TOOLS = {
    "file_write",
    "file_edit",
    "command_exec",
    "git",
    "create_document",
    "create_spreadsheet",
}

_DECOMPOSE_PROMPT_TEMPLATE = """\
Decompose this goal into a concrete execution plan with specific tool calls.

Goal: {goal}

Available tools: {tools}

Return ONLY a JSON array of steps. Each step must have:
- "description": what this step does (human readable)
- "tool_name": which tool to call
- "tool_args": dict of arguments for the tool

Example:
[
  {{"description": "Read the current file", "tool_name": "file_read", \
"tool_args": {{"path": "src/main.py"}}}},
  {{"description": "Edit the import section", "tool_name": "file_edit",
    "tool_args": {{"path": "src/main.py", "old": "import os",
    "new": "import os\\nimport sys"}}}}
]

Return ONLY the JSON array, no markdown, no explanation."""


# ─── Data Models ─────────────────────────────────────────────────────────


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class AgentStep:
    """A single atomic action within a plan."""

    index: int
    description: str
    tool_name: str
    tool_args: dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    result: str = ""
    error: str = ""


@dataclass
class AgentPlan:
    """An execution plan with ordered steps."""

    goal: str
    steps: list[AgentStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    max_tool_calls: int = MAX_TOOL_CALLS
    total_tool_calls: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def progress(self) -> dict:
        """Return progress summary."""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in self.steps if s.status == StepStatus.SKIPPED)
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "remaining": total - completed - failed - skipped,
            "tool_calls": self.total_tool_calls,
            "max_tool_calls": self.max_tool_calls,
        }

    def to_dict(self) -> dict:
        """Serialize plan to dict (safe for external exposure)."""
        return {
            "goal": self.goal,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "steps": [
                {
                    "index": s.index,
                    "description": s.description,
                    "tool_name": s.tool_name,
                    "tool_args": s.tool_args,
                    "status": s.status.value,
                    "result": s.result[:_RESULT_TRUNCATE_LIMIT] if s.result else "",
                    "error": s.error.split(":")[0] if s.error else "",
                }
                for s in self.steps
            ],
        }


# ─── Agent Session ───────────────────────────────────────────────────────


class AgentSession:
    """Encapsulates agent state — current plan and interrupt flag.

    Replaces module-level global state for better testability.
    """

    def __init__(self) -> None:
        self.current_plan: AgentPlan | None = None
        self.interrupt_requested: bool = False

    def get_plan(self) -> AgentPlan | None:
        """Return the current active plan, if any."""
        return self.current_plan

    def set_plan(self, plan: AgentPlan) -> None:
        """Set the current plan and reset interrupt flag."""
        self.current_plan = plan
        self.interrupt_requested = False

    def request_interrupt(self) -> None:
        """Signal the agent loop to pause at the next step boundary."""
        self.interrupt_requested = True

    def clear(self) -> None:
        """Clear the current plan and reset state."""
        self.current_plan = None
        self.interrupt_requested = False


# Default singleton session (backward-compatible with global state)
_session = AgentSession()


# ─── Backward-compatible global accessors ────────────────────────────────


def get_current_plan() -> AgentPlan | None:
    """Return the current active plan, if any."""
    return _session.get_plan()


def request_interrupt() -> None:
    """Signal the agent loop to pause at the next step boundary."""
    _session.request_interrupt()


def clear_plan() -> None:
    """Clear the current plan."""
    _session.clear()


# ─── Tool List ───────────────────────────────────────────────────────────


def _get_available_tools() -> str:
    """Build tool names list dynamically from the registry."""
    try:
        from .tools.registry import TOOLS_SPEC

        return ", ".join(
            spec.get("function", {}).get("name", "") for spec in TOOLS_SPEC if spec.get("function", {}).get("name")
        )
    except ImportError:
        log.debug("Registry not available, using fallback tool list")
        return (
            "file_read, file_write, file_edit, list_files, grep, "
            "command_exec, web_search, memory_save, memory_search, git, think, question"
        )


# ─── Decomposition ──────────────────────────────────────────────────────


def _build_decompose_prompt(goal: str) -> str:
    """Build the prompt for LLM plan decomposition."""
    tools = _get_available_tools()
    return _DECOMPOSE_PROMPT_TEMPLATE.format(goal=goal, tools=tools)


async def _collect_stream_response(messages: list[dict], model: str) -> str:
    """Collect full text response from streaming LLM chat."""
    from .llm.ollama import stream_chat

    full_response: list[str] = []
    async for chunk in stream_chat(messages, model, use_tools=False):
        try:
            line = chunk.strip()
            if line.startswith("data: "):
                line = line[6:]
            data = json.loads(line)
            if "content" in data:
                full_response.append(data["content"])
        except (json.JSONDecodeError, KeyError, TypeError):
            log.debug("Skipping unparseable SSE chunk: %s", chunk[:100])

    return "".join(full_response).strip()


async def decompose_goal(goal: str, model: str) -> AgentPlan:
    """Use the LLM to decompose a goal into an execution plan.

    Sends the goal to the LLM with a structured prompt requesting
    a JSON plan. Parses the response into an AgentPlan.
    """
    prompt = _build_decompose_prompt(goal)
    messages = [{"role": "user", "content": prompt}]
    response_text = await _collect_stream_response(messages, model)

    steps_data = _parse_plan_json(response_text)

    plan = AgentPlan(goal=goal)
    for i, step_data in enumerate(steps_data):
        plan.steps.append(
            AgentStep(
                index=i + 1,
                description=step_data.get("description", f"Step {i + 1}"),
                tool_name=step_data.get("tool_name", "think"),
                tool_args=step_data.get("tool_args", {}),
            )
        )

    if not plan.steps:
        raise ValueError("LLM failed to generate a valid plan. Try rephrasing the goal.")

    return plan


def _parse_plan_json(text: str) -> list[dict]:
    """Extract JSON array from LLM response, handling markdown code blocks."""
    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    if "```" in text:
        blocks = text.split("```")
        for block in blocks:
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                result = json.loads(block)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                continue

    # Try finding array brackets
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []


# ─── Execution ───────────────────────────────────────────────────────────


def _check_preconditions(
    plan: AgentPlan,
    step: AgentStep,
    session: AgentSession,
) -> dict | None:
    """Check interrupt, tool limit, and permissions before a step.

    Returns an event dict to yield if execution should stop/skip, or None to proceed.
    """
    # Check for interrupt
    if session.interrupt_requested:
        plan.status = PlanStatus.PAUSED
        return {
            "type": "agent_paused",
            "step": step.index,
            "reason": "User interrupt requested",
            "plan": plan.to_dict(),
        }

    # Check tool call limit
    if plan.total_tool_calls >= plan.max_tool_calls:
        plan.status = PlanStatus.ABORTED
        return {
            "type": "agent_aborted",
            "reason": f"Maximum tool calls ({plan.max_tool_calls}) reached",
            "plan": plan.to_dict(),
        }

    # Permission check — deny
    perm = check_permission(step.tool_name)
    if not perm.allowed and perm.level == "deny":
        step.status = StepStatus.FAILED
        step.error = f"Tool '{step.tool_name}' is denied by permissions"
        return {"type": "agent_step_error", "step": step.index, "error": step.error}

    # Permission check — ask (needs confirmation)
    if not perm.allowed and perm.level == "ask":
        plan.status = PlanStatus.PAUSED
        return {
            "type": "agent_paused",
            "step": step.index,
            "reason": f"Permission required for '{step.tool_name}'",
            "tool": step.tool_name,
            "plan": plan.to_dict(),
        }

    return None


def _snapshot_if_destructive(step: AgentStep) -> None:
    """Create an undo snapshot if the step uses a destructive tool."""
    if step.tool_name in _DESTRUCTIVE_TOOLS:
        target_path = step.tool_args.get("path", "")
        if target_path:
            save_snapshot(target_path)


async def _execute_step(step: AgentStep) -> str:
    """Execute a single step and return the result string."""
    from .tools.registry import execute_tool

    result = await execute_tool(step.tool_name, step.tool_args)
    return result if isinstance(result, str) else str(result)


async def execute_plan(
    plan: AgentPlan,
    session: AgentSession | None = None,
) -> AsyncGenerator[dict, None]:
    """Execute a plan step by step, yielding progress events.

    Event types:
    - agent_step_start: step is beginning
    - agent_step_complete: step finished successfully
    - agent_step_error: step failed
    - agent_paused: execution paused (interrupt or permission)
    - agent_complete: all steps done
    - agent_aborted: execution aborted (max calls or user request)
    """
    if session is None:
        session = _session

    session.set_plan(plan)
    plan.status = PlanStatus.EXECUTING

    start_changeset(f"agent:{plan.goal[:_GOAL_LABEL_LIMIT]}")

    for step in plan.steps:
        # Pre-checks (interrupt, limits, permissions)
        stop_event = _check_preconditions(plan, step, session)
        if stop_event:
            # Denied steps emit error and continue; others stop execution
            if stop_event["type"] == "agent_step_error":
                yield stop_event
                continue
            yield stop_event
            return

        # Start step
        step.status = StepStatus.IN_PROGRESS
        yield {
            "type": "agent_step_start",
            "step": step.index,
            "description": step.description,
            "tool": step.tool_name,
        }

        # Snapshot for destructive tools
        _snapshot_if_destructive(step)

        # Execute
        try:
            result = await _execute_step(step)
            plan.total_tool_calls += 1
            step.status = StepStatus.COMPLETED
            step.result = result
            yield {
                "type": "agent_step_complete",
                "step": step.index,
                "result": step.result[:_RESULT_TRUNCATE_LIMIT],
            }
        except Exception as e:
            plan.total_tool_calls += 1
            step.status = StepStatus.FAILED
            # Log full error internally but only expose error type to client
            log.error("Agent step %d failed: %s", step.index, e)
            step.error = f"{type(e).__name__}: {e}"  # noqa: TRY401
            yield {
                "type": "agent_step_error",
                "step": step.index,
                "error": f"Step failed ({type(e).__name__})",
                "plan": plan.to_dict(),
            }
            # Don't abort on individual step failure — continue to next

    # All steps processed
    plan.status = PlanStatus.COMPLETED
    yield {
        "type": "agent_complete",
        "plan": plan.to_dict(),
    }
