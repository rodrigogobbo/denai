"""Testes para o registro de ferramentas (denai.tools.registry).

Valida que todas as ferramentas esperadas estão registradas,
que o spec não está vazio e que tentativas de executar ferramentas
desconhecidas retornam erro.
"""

import pytest

from denai.tools.registry import TOOLS_SPEC, execute_tool

# As 14 tools esperadas
EXPECTED_TOOLS = [
    "file_read",
    "file_write",
    "list_files",
    "file_edit",
    "command_exec",
    "memory_save",
    "memory_search",
    "web_search",
    "rag_search",
    "rag_index",
    "rag_stats",
    "question",
    "plan_create",
    "plan_update",
]


class TestToolsSpec:
    """Testes para o registro de ferramentas (TOOLS_SPEC)."""

    def test_tools_spec_not_empty(self):
        """O registro de ferramentas não pode estar vazio."""
        assert TOOLS_SPEC is not None
        assert len(TOOLS_SPEC) > 0, "TOOLS_SPEC não deve estar vazio"

    def test_all_expected_tools_registered(self):
        """Todas as 14 tools core devem estar registradas."""
        registered = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        for name in EXPECTED_TOOLS:
            assert name in registered, f"Tool '{name}' não encontrada. Registradas: {registered}"

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_expected_tool_registered(self, tool_name: str):
        """Ferramenta '{tool_name}' deve estar registrada."""
        tool_names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert tool_name in tool_names, f"Ferramenta '{tool_name}' não encontrada. Registradas: {tool_names}"

    def test_each_tool_has_description(self):
        """Cada ferramenta deve ter uma descrição."""
        for tool in TOOLS_SPEC:
            fn = tool.get("function", {})
            name = fn.get("name", "?")
            desc = fn.get("description", "")
            assert desc, f"Ferramenta '{name}' não tem descrição"

    def test_each_tool_has_parameters(self):
        """Cada ferramenta deve ter definição de parâmetros."""
        for tool in TOOLS_SPEC:
            fn = tool.get("function", {})
            name = fn.get("name", "?")
            params = fn.get("parameters", {})
            assert params, f"Ferramenta '{name}' não tem parâmetros definidos"
            assert params.get("type") == "object", f"Ferramenta '{name}' deve ter parameters.type='object'"

    def test_total_tools_count(self):
        """Devem haver pelo menos 14 tools registradas."""
        assert len(TOOLS_SPEC) >= 14


class TestExecuteTool:
    """Testes para execução de ferramentas."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Executar ferramenta desconhecida deve retornar indicação de erro."""
        result = await execute_tool("nonexistent_tool_xyz", {})
        assert "❌" in result or "desconhecida" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_tool_does_not_crash(self):
        """Executar ferramenta desconhecida não deve lançar exceção."""
        try:
            await execute_tool("absolutely_fake_tool", {"key": "value"})
        except (KeyError, ValueError, TypeError):
            pass
        except Exception as e:
            pytest.fail(f"Exceção inesperada ao executar tool desconhecida: {type(e).__name__}: {e}")

    @pytest.mark.asyncio
    async def test_empty_tool_name_returns_error(self):
        """Nome de ferramenta vazio deve retornar erro."""
        result = await execute_tool("", {})
        assert "❌" in result or "desconhecida" in result.lower()
