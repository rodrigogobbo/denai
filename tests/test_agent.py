"""Tests for agent loop — plan decomposition, execution, interrupts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from denai.agent import (
    AgentPlan,
    AgentStep,
    PlanStatus,
    StepStatus,
    _parse_plan_json,
    clear_plan,
    execute_plan,
    get_current_plan,
    request_interrupt,
)

# ─── Data model tests ────────────────────────────────────────────────────


class TestStepStatus:
    """Test StepStatus enum."""

    def test_values(self):
        assert StepStatus.PENDING == "pending"
        assert StepStatus.IN_PROGRESS == "in_progress"
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"


class TestPlanStatus:
    """Test PlanStatus enum."""

    def test_values(self):
        assert PlanStatus.DRAFT == "draft"
        assert PlanStatus.APPROVED == "approved"
        assert PlanStatus.EXECUTING == "executing"
        assert PlanStatus.PAUSED == "paused"
        assert PlanStatus.COMPLETED == "completed"
        assert PlanStatus.FAILED == "failed"
        assert PlanStatus.ABORTED == "aborted"


class TestAgentStep:
    """Test AgentStep dataclass."""

    def test_defaults(self):
        step = AgentStep(index=1, description="test", tool_name="think")
        assert step.status == StepStatus.PENDING
        assert step.result == ""
        assert step.error == ""
        assert step.tool_args == {}

    def test_with_args(self):
        step = AgentStep(
            index=2,
            description="read file",
            tool_name="file_read",
            tool_args={"path": "src/main.py"},
        )
        assert step.tool_args["path"] == "src/main.py"


class TestAgentPlan:
    """Test AgentPlan dataclass."""

    def test_empty_plan(self):
        plan = AgentPlan(goal="test goal")
        assert plan.goal == "test goal"
        assert plan.steps == []
        assert plan.status == PlanStatus.DRAFT
        assert plan.max_tool_calls == 50
        assert plan.total_tool_calls == 0
        assert plan.created_at

    def test_progress_empty(self):
        plan = AgentPlan(goal="test")
        progress = plan.progress
        assert progress["total"] == 0
        assert progress["completed"] == 0
        assert progress["remaining"] == 0

    def test_progress_with_steps(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="s1", tool_name="think", status=StepStatus.COMPLETED),
            AgentStep(index=2, description="s2", tool_name="think", status=StepStatus.FAILED),
            AgentStep(index=3, description="s3", tool_name="think", status=StepStatus.PENDING),
        ]
        progress = plan.progress
        assert progress["total"] == 3
        assert progress["completed"] == 1
        assert progress["failed"] == 1
        assert progress["remaining"] == 1

    def test_to_dict(self):
        plan = AgentPlan(goal="test goal")
        plan.steps = [
            AgentStep(index=1, description="step 1", tool_name="think"),
        ]
        d = plan.to_dict()
        assert d["goal"] == "test goal"
        assert d["status"] == "draft"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["index"] == 1
        assert d["steps"][0]["tool_name"] == "think"
        assert "progress" in d
        assert "created_at" in d

    def test_to_dict_truncates_result(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(
                index=1,
                description="s1",
                tool_name="think",
                result="x" * 1000,
            ),
        ]
        d = plan.to_dict()
        assert len(d["steps"][0]["result"]) == 500


# ─── Global state tests ─────────────────────────────────────────────────


class TestGlobalState:
    """Test global plan state management."""

    def test_no_plan_initially(self):
        clear_plan()
        assert get_current_plan() is None

    def test_clear_plan(self):
        clear_plan()
        assert get_current_plan() is None


# ─── Plan JSON parsing ──────────────────────────────────────────────────


class TestParsePlanJson:
    """Test _parse_plan_json extraction."""

    def test_valid_json_array(self):
        text = '[{"description": "s1", "tool_name": "think", "tool_args": {}}]'
        result = _parse_plan_json(text)
        assert len(result) == 1
        assert result[0]["tool_name"] == "think"

    def test_json_in_markdown_block(self):
        text = '```json\n[{"description": "s1", "tool_name": "think", "tool_args": {}}]\n```'
        result = _parse_plan_json(text)
        assert len(result) == 1

    def test_json_with_surrounding_text(self):
        text = 'Here is the plan:\n[{"description": "s1", "tool_name": "think", "tool_args": {}}]\nDone!'
        result = _parse_plan_json(text)
        assert len(result) == 1

    def test_invalid_json(self):
        result = _parse_plan_json("not json at all")
        assert result == []

    def test_empty_string(self):
        result = _parse_plan_json("")
        assert result == []

    def test_json_object_not_array(self):
        result = _parse_plan_json('{"key": "value"}')
        assert result == []

    def test_multiple_code_blocks(self):
        text = (
            "```python\nprint('hi')\n```\n"
            "```json\n"
            '[{"description": "s1", "tool_name": "file_read", "tool_args": {"path": "a.py"}}]\n'
            "```"
        )
        result = _parse_plan_json(text)
        assert len(result) == 1
        assert result[0]["tool_name"] == "file_read"


# ─── Plan execution tests ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestExecutePlan:
    """Test execute_plan generator."""

    async def _collect_events(self, plan):
        """Collect all events from execute_plan."""
        events = []
        async for event in execute_plan(plan):
            events.append(event)
        return events

    async def test_empty_plan_completes(self):
        plan = AgentPlan(goal="nothing")
        plan.status = PlanStatus.APPROVED
        events = await self._collect_events(plan)
        assert len(events) == 1
        assert events[0]["type"] == "agent_complete"
        assert plan.status == PlanStatus.COMPLETED

    async def test_single_step_success(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="think", tool_name="think", tool_args={"thought": "ok"}),
        ]

        with patch("denai.tools.registry.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "thought processed"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

        # Should have: step_start, step_complete, agent_complete
        types = [e["type"] for e in events]
        assert "agent_step_start" in types
        assert "agent_step_complete" in types
        assert "agent_complete" in types
        assert plan.total_tool_calls == 1

    async def test_step_failure_continues(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="fail", tool_name="file_read"),
            AgentStep(index=2, description="ok", tool_name="think"),
        ]

        call_count = 0

        async def mock_exec(tool_name, tool_args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("file not found")
            return "ok"

        with patch("denai.tools.registry.execute_tool", side_effect=mock_exec):
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

        types = [e["type"] for e in events]
        assert "agent_step_error" in types
        assert "agent_step_complete" in types
        assert "agent_complete" in types
        assert plan.steps[0].status == StepStatus.FAILED
        assert plan.steps[1].status == StepStatus.COMPLETED

    async def test_permission_denied_skips(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="write", tool_name="file_write"),
        ]

        with patch("denai.agent.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": False, "level": "deny", "reason": "blocked"})()
            events = await self._collect_events(plan)

        types = [e["type"] for e in events]
        assert "agent_step_error" in types
        assert plan.steps[0].status == StepStatus.FAILED

    async def test_permission_ask_pauses(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="exec", tool_name="command_exec"),
        ]

        with patch("denai.agent.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": False, "level": "ask", "reason": "needs confirm"})()
            events = await self._collect_events(plan)

        assert len(events) == 1
        assert events[0]["type"] == "agent_paused"
        assert plan.status == PlanStatus.PAUSED

    async def test_interrupt_pauses(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(index=1, description="s1", tool_name="think"),
            AgentStep(index=2, description="s2", tool_name="think"),
        ]

        call_count = 0

        async def mock_exec_and_interrupt(tool_name, tool_args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # After first step completes, request interrupt
                request_interrupt()
            return "ok"

        with patch("denai.tools.registry.execute_tool", side_effect=mock_exec_and_interrupt):
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

        types = [e["type"] for e in events]
        assert "agent_paused" in types
        assert plan.status == PlanStatus.PAUSED

    async def test_max_tool_calls_aborts(self):
        plan = AgentPlan(goal="test", max_tool_calls=1)
        plan.steps = [
            AgentStep(index=1, description="s1", tool_name="think"),
            AgentStep(index=2, description="s2", tool_name="think"),
        ]

        with patch("denai.tools.registry.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "ok"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

        types = [e["type"] for e in events]
        # First step executes, second triggers abort
        assert "agent_step_complete" in types
        assert "agent_aborted" in types

    async def test_destructive_tool_snapshots(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(
                index=1,
                description="write",
                tool_name="file_write",
                tool_args={"path": "/tmp/test.txt"},
            ),
        ]

        with patch("denai.tools.registry.execute_tool", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "ok"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                with patch("denai.agent.save_snapshot") as mock_snap:
                    await self._collect_events(plan)
                    mock_snap.assert_called_once_with("/tmp/test.txt")
