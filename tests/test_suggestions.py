"""Testes para suggest_skill, suggest_plugin e _maybe_suggestion_event."""

from __future__ import annotations

import json

import pytest

from denai.tools.suggestions import _SUGGESTION_PREFIX, suggest_plugin, suggest_skill

# ─── suggest_skill ─────────────────────────────────────────────────────────


class TestSuggestSkill:
    @pytest.mark.asyncio
    async def test_returns_suggestion_prefix(self):
        result = await suggest_skill({"skill_name": "security", "reason": "Análise de vulnerabilidades"})
        assert result.startswith(_SUGGESTION_PREFIX)

    @pytest.mark.asyncio
    async def test_payload_is_valid_json(self):
        result = await suggest_skill({"skill_name": "reviewer", "reason": "Code review"})
        payload = result[len(_SUGGESTION_PREFIX) :]
        data = json.loads(payload)
        assert data["type"] == "skill"
        assert data["id"] == "reviewer"
        assert data["reason"] == "Code review"

    @pytest.mark.asyncio
    async def test_missing_skill_name_returns_error(self):
        result = await suggest_skill({"reason": "motivo"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_missing_reason_returns_error(self):
        result = await suggest_skill({"skill_name": "security"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_empty_skill_name_returns_error(self):
        result = await suggest_skill({"skill_name": "  ", "reason": "motivo"})
        assert "❌" in result


# ─── suggest_plugin ────────────────────────────────────────────────────────


class TestSuggestPlugin:
    @pytest.mark.asyncio
    async def test_returns_suggestion_prefix(self):
        result = await suggest_plugin({"plugin_id": "browser", "reason": "Navegar na web"})
        assert result.startswith(_SUGGESTION_PREFIX)

    @pytest.mark.asyncio
    async def test_payload_type_is_plugin(self):
        result = await suggest_plugin({"plugin_id": "databricks", "reason": "Queries SQL"})
        payload = result[len(_SUGGESTION_PREFIX) :]
        data = json.loads(payload)
        assert data["type"] == "plugin"
        assert data["id"] == "databricks"
        assert data["reason"] == "Queries SQL"

    @pytest.mark.asyncio
    async def test_missing_plugin_id_returns_error(self):
        result = await suggest_plugin({"reason": "motivo"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_missing_reason_returns_error(self):
        result = await suggest_plugin({"plugin_id": "browser"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_empty_plugin_id_returns_error(self):
        result = await suggest_plugin({"plugin_id": "", "reason": "motivo"})
        assert "❌" in result


# ─── _maybe_suggestion_event ───────────────────────────────────────────────


class TestMaybeSuggestionEvent:
    def test_detects_suggestion_prefix(self):
        from denai.llm.ollama import _maybe_suggestion_event

        payload = json.dumps({"type": "skill", "id": "security", "reason": "test"})
        result = f"{_SUGGESTION_PREFIX}{payload}"
        event = _maybe_suggestion_event(result)
        assert event is not None
        data = json.loads(event)
        assert "suggestion" in data
        assert data["suggestion"]["type"] == "skill"
        assert data["suggestion"]["id"] == "security"

    def test_returns_none_for_normal_result(self):
        from denai.llm.ollama import _maybe_suggestion_event

        assert _maybe_suggestion_event("✅ Arquivo salvo com sucesso") is None
        assert _maybe_suggestion_event("❌ Erro ao processar") is None
        assert _maybe_suggestion_event("Resultado normal") is None

    def test_returns_none_for_empty_string(self):
        from denai.llm.ollama import _maybe_suggestion_event

        assert _maybe_suggestion_event("") is None

    def test_handles_invalid_json_gracefully(self):
        from denai.llm.ollama import _maybe_suggestion_event

        result = _maybe_suggestion_event(f"{_SUGGESTION_PREFIX}not valid json {{")
        assert result is None

    def test_plugin_suggestion_event(self):
        from denai.llm.ollama import _maybe_suggestion_event

        payload = json.dumps({"type": "plugin", "id": "browser", "reason": "navegar"})
        result = f"{_SUGGESTION_PREFIX}{payload}"
        event = _maybe_suggestion_event(result)
        assert event is not None
        data = json.loads(event)
        assert data["suggestion"]["type"] == "plugin"


# ─── Registration ──────────────────────────────────────────────────────────


class TestSuggestionRegistration:
    def test_suggest_skill_in_registry(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "suggest_skill" in names

    def test_suggest_plugin_in_registry(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "suggest_plugin" in names

    def test_suggest_tools_not_in_plan_mode(self):
        from denai.modes import PLAN_MODE_TOOLS

        assert "suggest_skill" not in PLAN_MODE_TOOLS
        assert "suggest_plugin" not in PLAN_MODE_TOOLS
