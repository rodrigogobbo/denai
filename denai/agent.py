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

MAX_TOOL_CALLS = 50

# Tools that modify state (require undo snapshots)
_DESTRUCTIVE_TOOLS = {"file_write", "file_edit", "command_exec", "git", "create_document", "create_spreadsheet"}


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
                    "result": s.result[:500] if s.result else "",
                    "error": s.error.split(":")[0] if s.error else "",
                }
                for s in self.steps
            ],
        }


# ── Global state ──────────────────────────────────────────────────────────
_current_plan: AgentPlan | None = None
_interrupt_requested: bool = False


def get_current_plan() -> AgentPlan | None:
    """Return the current active plan, if any."""
    return _current_plan


def request_interrupt() -> None:
    """Signal the agent loop to pause at the next step boundary."""
    global _interrupt_requested
    _interrupt_requested = True


def clear_plan() -> None:
    """Clear the current plan."""
    global _current_plan, _interrupt_requested
    _current_plan = None
    _interrupt_requested = False


async def decompose_goal(goal: str, model: str) -> AgentPlan:
    """Use the LLM to decompose a goal into an execution plan.

    Sends the goal to the LLM with a structured prompt requesting
    a JSON plan. Parses the response into an AgentPlan.
    """
    from .llm.ollama import stream_chat

    prompt = f"""Decompose this goal into a concrete execution plan with specific tool calls.

Goal: {goal}

Available tools: file_read, file_write, file_edit, list_files, grep,
command_exec, web_search, memory_save, memory_search, git, think, question

Return ONLY a JSON array of steps. Each step must have:
- "description": what this step does (human readable)
- "tool_name": which tool to call
- "tool_args": dict of arguments for the tool

Example:
[
  {{"description": "Read the current file", "tool_name": "file_read", "tool_args": {{"path": "src/main.py"}}}},
  {{"description": "Edit the import section", "tool_name": "file_edit",
    "tool_args": {{"path": "src/main.py", "old": "import os",
    "new": "import os\\nimport sys"}}}}
]

Return ONLY the JSON array, no markdown, no explanation."""

    messages = [{"role": "user", "content": prompt}]

    full_response = []
    async for chunk in stream_chat(messages, model, use_tools=False):
        try:
            line = chunk.strip()
            if line.startswith("data: "):
                line = line[6:]
            data = json.loads(line)
            if "content" in data:
                full_response.append(data["content"])
        except Exception:
            pass

    response_text = "".join(full_response).strip()

    # Try to extract JSON from response
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


async def execute_plan(plan: AgentPlan) -> AsyncGenerator[dict, None]:
    """Execute a plan step by step, yielding progress events.

    Event types:
    - agent_step_start: step is beginning
    - agent_step_complete: step finished successfully
    - agent_step_error: step failed
    - agent_paused: execution paused (interrupt or permission)
    - agent_complete: all steps done
    - agent_aborted: execution aborted (max calls or user request)
    """
    global _current_plan, _interrupt_requested
    _current_plan = plan
    _interrupt_requested = False
    plan.status = PlanStatus.EXECUTING

    from .tools.registry import execute_tool

    start_changeset(f"agent:{plan.goal[:50]}")

    for step in plan.steps:
        # Check for interrupt
        if _interrupt_requested:
            plan.status = PlanStatus.PAUSED
            yield {
                "type": "agent_paused",
                "step": step.index,
                "reason": "User interrupt requested",
                "plan": plan.to_dict(),
            }
            return

        # Check tool call limit
        if plan.total_tool_calls >= plan.max_tool_calls:
            plan.status = PlanStatus.ABORTED
            yield {
                "type": "agent_aborted",
                "reason": f"Maximum tool calls ({plan.max_tool_calls}) reached",
                "plan": plan.to_dict(),
            }
            return

        # Permission check
        perm = check_permission(step.tool_name)
        if not perm.allowed and perm.level == "deny":
            step.status = StepStatus.FAILED
            step.error = f"Tool '{step.tool_name}' is denied by permissions"
            yield {"type": "agent_step_error", "step": step.index, "error": step.error}
            continue

        if not perm.allowed and perm.level == "ask":
            plan.status = PlanStatus.PAUSED
            yield {
                "type": "agent_paused",
                "step": step.index,
                "reason": f"Permission required for '{step.tool_name}'",
                "tool": step.tool_name,
                "plan": plan.to_dict(),
            }
            return

        # Start step
        step.status = StepStatus.IN_PROGRESS
        yield {
            "type": "agent_step_start",
            "step": step.index,
            "description": step.description,
            "tool": step.tool_name,
        }

        # Create undo snapshot for destructive tools
        if step.tool_name in _DESTRUCTIVE_TOOLS:
            # For file operations, snapshot the target file
            target_path = step.tool_args.get("path", "")
            if target_path:
                save_snapshot(target_path)

        # Execute
        try:
            result = await execute_tool(step.tool_name, step.tool_args)
            plan.total_tool_calls += 1
            step.status = StepStatus.COMPLETED
            step.result = result if isinstance(result, str) else str(result)
            yield {
                "type": "agent_step_complete",
                "step": step.index,
                "result": step.result[:500],
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
            # The caller (route) can decide to abort based on this event

    # All steps processed
    plan.status = PlanStatus.COMPLETED
    yield {
        "type": "agent_complete",
        "plan": plan.to_dict(),
    }
