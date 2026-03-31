"""Testes para personas e subagent tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from denai.personas import _parse_persona_file, discover_personas, get_persona
from denai.tools.subagent import _resolve_system_prompt, subagent

# ─── personas.py ───────────────────────────────────────────────────────────


class TestParsePersonaFile:
    def test_parse_basic_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\nname: myagent\ndescription: Does stuff\n---\nYou are a specialist.")
        p = _parse_persona_file(f)
        assert p is not None
        assert p.name == "myagent"
        assert p.description == "Does stuff"
        assert p.system_prompt == "You are a specialist."

    def test_parse_no_frontmatter(self, tmp_path):
        f = tmp_path / "simple.md"
        f.write_text("You are a simple agent.")
        p = _parse_persona_file(f)
        assert p is not None
        assert p.name == "simple"
        assert p.system_prompt == "You are a simple agent."

    def test_parse_empty_file_returns_none(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        p = _parse_persona_file(f)
        assert p is None

    def test_parse_uses_filename_as_default_name(self, tmp_path):
        f = tmp_path / "fallback.md"
        f.write_text("---\ndescription: test\n---\nContent.")
        p = _parse_persona_file(f)
        assert p is not None
        assert p.name == "fallback"

    def test_parse_source_attribute(self, tmp_path):
        f = tmp_path / "x.md"
        f.write_text("Content")
        p = _parse_persona_file(f, source="custom")
        assert p is not None
        assert p.source == "custom"


class TestDiscoverPersonas:
    def test_discovers_bundled_personas(self):
        personas = discover_personas()
        names = [p.name for p in personas]
        assert "security" in names
        assert "reviewer" in names
        assert "writer" in names
        assert "data" in names

    def test_custom_overrides_bundled(self, tmp_path):
        custom_dir = tmp_path / "personas"
        custom_dir.mkdir()
        (custom_dir / "security.md").write_text(
            "---\nname: security\ndescription: Custom\n---\nCustom security prompt."
        )
        with patch("denai.personas.PERSONAS_DIR", custom_dir):
            personas = discover_personas()
        security = next(p for p in personas if p.name == "security")
        assert security.source == "custom"
        assert security.system_prompt == "Custom security prompt."

    def test_empty_custom_dir_returns_bundled(self, tmp_path):
        empty = tmp_path / "personas"
        empty.mkdir()
        with patch("denai.personas.PERSONAS_DIR", empty):
            personas = discover_personas()
        assert len(personas) >= 4  # pelo menos as 4 bundled


class TestGetPersona:
    def test_get_existing_persona(self):
        p = get_persona("security")
        assert p is not None
        assert p.name == "security"

    def test_get_case_insensitive(self):
        p = get_persona("REVIEWER")
        assert p is not None
        assert p.name == "reviewer"

    def test_get_nonexistent_returns_none(self):
        p = get_persona("nonexistent-xyz-123")
        assert p is None

    def test_all_bundled_personas_have_system_prompt(self):
        for name in ("security", "reviewer", "writer", "data"):
            p = get_persona(name)
            assert p is not None, f"Persona '{name}' não encontrada"
            assert len(p.system_prompt) > 50, f"Persona '{name}' tem system_prompt muito curto"


# ─── _resolve_system_prompt ─────────────────────────────────────────────────


class TestResolveSystemPrompt:
    def test_override_takes_priority(self):
        result = _resolve_system_prompt("security", "Custom override")
        assert result == "Custom override"

    def test_persona_name_resolved(self):
        result = _resolve_system_prompt("security", "")
        p = get_persona("security")
        assert result == p.system_prompt

    def test_unknown_persona_uses_fallback(self):
        result = _resolve_system_prompt("nonexistent-xyz", "")
        assert len(result) > 10  # fallback genérico

    def test_empty_args_uses_fallback(self):
        result = _resolve_system_prompt("", "")
        assert len(result) > 10

    def test_override_beats_valid_persona(self):
        result = _resolve_system_prompt("reviewer", "My custom prompt")
        assert result == "My custom prompt"


# ─── subagent tool ─────────────────────────────────────────────────────────


class TestSubagentTool:
    @pytest.mark.asyncio
    async def test_missing_goal_returns_error(self):
        result = await subagent({})
        assert "❌" in result
        assert "goal" in result

    @pytest.mark.asyncio
    async def test_empty_goal_returns_error(self):
        result = await subagent({"goal": "   "})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        import asyncio

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(200)
            return "never"

        with patch("denai.tools.subagent._run_subagent", slow_run):
            with patch("denai.tools.subagent.SUBAGENT_TIMEOUT", 0.01):
                result = await subagent({"goal": "do something"})
        assert "❌" in result
        assert "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_successful_run_returns_response(self):
        async def mock_run(goal, system_prompt, model):
            return f"Resultado para: {goal}"

        with patch("denai.tools.subagent._run_subagent", mock_run):
            result = await subagent({"goal": "Analise auth.py", "persona": "security"})
        assert "Resultado para: Analise auth.py" in result

    @pytest.mark.asyncio
    async def test_exception_in_run_returns_error(self):
        async def failing_run(*args, **kwargs):
            raise RuntimeError("LLM unavailable")

        with patch("denai.tools.subagent._run_subagent", failing_run):
            result = await subagent({"goal": "something"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_uses_custom_system_prompt(self):
        captured = {}

        async def mock_run(goal, system_prompt, model):
            captured["system_prompt"] = system_prompt
            return "done"

        with patch("denai.tools.subagent._run_subagent", mock_run):
            await subagent({"goal": "something", "system_prompt": "Be very strict."})

        assert captured["system_prompt"] == "Be very strict."

    @pytest.mark.asyncio
    async def test_uses_persona_system_prompt(self):
        captured = {}

        async def mock_run(goal, system_prompt, model):
            captured["system_prompt"] = system_prompt
            return "done"

        with patch("denai.tools.subagent._run_subagent", mock_run):
            await subagent({"goal": "review code", "persona": "reviewer"})

        p = get_persona("reviewer")
        assert captured["system_prompt"] == p.system_prompt

    @pytest.mark.asyncio
    async def test_inherits_default_model(self):
        captured = {}

        async def mock_run(goal, system_prompt, model):
            captured["model"] = model
            return "done"

        with patch("denai.tools.subagent._run_subagent", mock_run):
            await subagent({"goal": "something"})

        from denai.config import DEFAULT_MODEL

        assert captured["model"] == DEFAULT_MODEL

    @pytest.mark.asyncio
    async def test_custom_model_passed_through(self):
        captured = {}

        async def mock_run(goal, system_prompt, model):
            captured["model"] = model
            return "done"

        with patch("denai.tools.subagent._run_subagent", mock_run):
            await subagent({"goal": "something", "model": "llama3.2:3b"})

        assert captured["model"] == "llama3.2:3b"


# ─── subagent não recursivo ─────────────────────────────────────────────────


class TestSubagentNoRecursion:
    def test_subagent_not_in_its_own_tools(self):
        """Sub-agente não deve ter acesso à tool subagent (sem recursão)."""

        captured_tools: dict = {}

        async def mock_stream_chat(messages, model, use_tools, tools_spec, system_override):
            captured_tools["tools"] = tools_spec
            return
            yield  # noqa: E501 -- unreachable, makes this an async generator

        with patch("denai.llm.ollama.stream_chat", mock_stream_chat):
            import asyncio

            asyncio.get_event_loop().run_until_complete(subagent({"goal": "test no recursion"}))

        if captured_tools.get("tools") is not None:
            tool_names = [t.get("function", {}).get("name") for t in captured_tools["tools"]]
            assert "subagent" not in tool_names


# ─── Registration ───────────────────────────────────────────────────────────


class TestSubagentRegistration:
    def test_subagent_in_tools_spec(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "subagent" in names

    def test_subagent_not_in_plan_mode(self):
        from denai.modes import PLAN_MODE_TOOLS

        assert "subagent" not in PLAN_MODE_TOOLS
