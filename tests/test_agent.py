"""Tests for agent loop — plan decomposition, execution, interrupts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from denai.agent import (
    _GOAL_LABEL_LIMIT,
    _RESULT_TRUNCATE_LIMIT,
    AgentPlan,
    AgentSession,
    AgentStep,
    PlanStatus,
    StepStatus,
    _build_decompose_prompt,
    _check_preconditions,
    _get_available_tools,
    _parse_plan_json,
    _snapshot_if_destructive,
    clear_plan,
    execute_plan,
    get_current_plan,
)

# ─── Constants tests ────────────────────────────────────────────────────


class TestConstants:
    """Test module-level constants."""

    def test_result_truncate_limit(self):
        assert _RESULT_TRUNCATE_LIMIT == 500

    def test_goal_label_limit(self):
        assert _GOAL_LABEL_LIMIT == 50


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
        assert len(d["steps"][0]["result"]) == _RESULT_TRUNCATE_LIMIT

    def test_to_dict_sanitizes_error(self):
        plan = AgentPlan(goal="test")
        plan.steps = [
            AgentStep(
                index=1,
                description="s1",
                tool_name="think",
                error="RuntimeError: sensitive internal path /etc/secret",
            ),
        ]
        d = plan.to_dict()
        # Should only expose the error type, not the message
        assert d["steps"][0]["error"] == "RuntimeError"
        assert "sensitive" not in d["steps"][0]["error"]


# ─── AgentSession tests ──────────────────────────────────────────────────


class TestAgentSession:
    """Test AgentSession state management."""

    def test_initial_state(self):
        session = AgentSession()
        assert session.get_plan() is None
        assert session.interrupt_requested is False

    def test_set_plan(self):
        session = AgentSession()
        plan = AgentPlan(goal="test")
        session.set_plan(plan)
        assert session.get_plan() is plan
        assert session.interrupt_requested is False

    def test_set_plan_resets_interrupt(self):
        session = AgentSession()
        session.interrupt_requested = True
        session.set_plan(AgentPlan(goal="test"))
        assert session.interrupt_requested is False

    def test_request_interrupt(self):
        session = AgentSession()
        session.request_interrupt()
        assert session.interrupt_requested is True

    def test_clear(self):
        session = AgentSession()
        session.set_plan(AgentPlan(goal="test"))
        session.request_interrupt()
        session.clear()
        assert session.get_plan() is None
        assert session.interrupt_requested is False


# ─── Global state tests (backward compat) ───────────────────────────────


class TestGlobalState:
    """Test global plan state management."""

    def test_no_plan_initially(self):
        clear_plan()
        assert get_current_plan() is None

    def test_clear_plan(self):
        clear_plan()
        assert get_current_plan() is None


# ─── Tool list tests ────────────────────────────────────────────────────


class TestGetAvailableTools:
    """Test dynamic tool list generation."""

    def test_returns_string(self):
        tools = _get_available_tools()
        assert isinstance(tools, str)
        assert len(tools) > 0

    def test_fallback_on_import_error(self):
        with patch.dict("sys.modules", {"denai.tools.registry": None}):
            # Force re-import to trigger ImportError
            tools = _get_available_tools()
            assert "file_read" in tools


class TestBuildDecomposePrompt:
    """Test prompt building."""

    def test_includes_goal(self):
        prompt = _build_decompose_prompt("create a file")
        assert "create a file" in prompt

    def test_includes_tools(self):
        prompt = _build_decompose_prompt("test")
        assert "Available tools:" in prompt

    def test_includes_json_example(self):
        prompt = _build_decompose_prompt("test")
        assert "JSON array" in prompt


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


# ─── Precondition checks ────────────────────────────────────────────────


class TestCheckPreconditions:
    """Test _check_preconditions helper."""

    def test_no_issue_returns_none(self):
        plan = AgentPlan(goal="test")
        step = AgentStep(index=1, description="s1", tool_name="think")
        session = AgentSession()

        with patch("denai.agent.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
            result = _check_preconditions(plan, step, session)

        assert result is None

    def test_interrupt_returns_paused(self):
        plan = AgentPlan(goal="test")
        step = AgentStep(index=1, description="s1", tool_name="think")
        session = AgentSession()
        session.request_interrupt()

        result = _check_preconditions(plan, step, session)
        assert result is not None
        assert result["type"] == "agent_paused"
        assert plan.status == PlanStatus.PAUSED

    def test_max_calls_returns_aborted(self):
        plan = AgentPlan(goal="test", max_tool_calls=5)
        plan.total_tool_calls = 5
        step = AgentStep(index=1, description="s1", tool_name="think")
        session = AgentSession()

        result = _check_preconditions(plan, step, session)
        assert result is not None
        assert result["type"] == "agent_aborted"
        assert plan.status == PlanStatus.ABORTED

    def test_deny_returns_error(self):
        plan = AgentPlan(goal="test")
        step = AgentStep(index=1, description="s1", tool_name="file_write")
        session = AgentSession()

        with patch("denai.agent.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": False, "level": "deny", "reason": "blocked"})()
            result = _check_preconditions(plan, step, session)

        assert result is not None
        assert result["type"] == "agent_step_error"
        assert step.status == StepStatus.FAILED

    def test_ask_returns_paused(self):
        plan = AgentPlan(goal="test")
        step = AgentStep(index=1, description="s1", tool_name="command_exec")
        session = AgentSession()

        with patch("denai.agent.check_permission") as mock_perm:
            mock_perm.return_value = type("P", (), {"allowed": False, "level": "ask", "reason": "needs confirm"})()
            result = _check_preconditions(plan, step, session)

        assert result is not None
        assert result["type"] == "agent_paused"
        assert plan.status == PlanStatus.PAUSED


# ─── Snapshot tests ──────────────────────────────────────────────────────


class TestSnapshotIfDestructive:
    """Test _snapshot_if_destructive helper."""

    def test_destructive_tool_creates_snapshot(self):
        step = AgentStep(index=1, description="write", tool_name="file_write", tool_args={"path": "/tmp/x.txt"})
        with patch("denai.agent.save_snapshot") as mock_snap:
            _snapshot_if_destructive(step)
            mock_snap.assert_called_once_with("/tmp/x.txt")

    def test_non_destructive_tool_skips(self):
        step = AgentStep(index=1, description="read", tool_name="file_read", tool_args={"path": "/tmp/x.txt"})
        with patch("denai.agent.save_snapshot") as mock_snap:
            _snapshot_if_destructive(step)
            mock_snap.assert_not_called()

    def test_destructive_without_path_skips(self):
        step = AgentStep(index=1, description="exec", tool_name="command_exec", tool_args={"command": "ls"})
        with patch("denai.agent.save_snapshot") as mock_snap:
            _snapshot_if_destructive(step)
            mock_snap.assert_not_called()


# ─── Plan execution tests ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestExecutePlan:
    """Test execute_plan generator."""

    async def _collect_events(self, plan, session=None):
        """Collect all events from execute_plan."""
        events = []
        async for event in execute_plan(plan, session=session):
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

        with patch("denai.agent._execute_step", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "thought processed"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

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

        async def mock_exec(step):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("file not found")
            return "ok"

        with patch("denai.agent._execute_step", side_effect=mock_exec):
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

        session = AgentSession()
        call_count = 0

        async def mock_exec(step):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                session.request_interrupt()
            return "ok"

        with patch("denai.agent._execute_step", side_effect=mock_exec):
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan, session=session)

        types = [e["type"] for e in events]
        assert "agent_paused" in types
        assert plan.status == PlanStatus.PAUSED

    async def test_max_tool_calls_aborts(self):
        plan = AgentPlan(goal="test", max_tool_calls=1)
        plan.steps = [
            AgentStep(index=1, description="s1", tool_name="think"),
            AgentStep(index=2, description="s2", tool_name="think"),
        ]

        with patch("denai.agent._execute_step", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "ok"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                events = await self._collect_events(plan)

        types = [e["type"] for e in events]
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

        with patch("denai.agent._execute_step", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = "ok"
            with patch("denai.agent.check_permission") as mock_perm:
                mock_perm.return_value = type("P", (), {"allowed": True, "level": "allow", "reason": ""})()
                with patch("denai.agent.save_snapshot") as mock_snap:
                    await self._collect_events(plan)
                    mock_snap.assert_called_once_with("/tmp/test.txt")

    async def test_uses_custom_session(self):
        """Test that execute_plan works with a custom session."""
        plan = AgentPlan(goal="test")
        session = AgentSession()

        events = await self._collect_events(plan, session=session)
        assert events[0]["type"] == "agent_complete"
        assert session.get_plan() is plan
