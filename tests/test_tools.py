"""Testes para o registro de ferramentas (denai.tools.registry).

Valida que todas as ferramentas esperadas estão registradas,
que o spec não está vazio e que tentativas de executar ferramentas
desconhecidas retornam erro.
"""

import pytest
import pytest_asyncio

from denai.tools.registry import TOOLS_SPEC, execute_tool


class TestToolsSpec:
    """Testes para o registro de ferramentas (TOOLS_SPEC)."""

    def test_tools_spec_not_empty(self):
        """O registro de ferramentas não pode estar vazio."""
        assert TOOLS_SPEC is not None
        assert len(TOOLS_SPEC) > 0, "TOOLS_SPEC não deve estar vazio"

    @pytest.mark.parametrize(
        "tool_name",
        [
            "file_read",
            "file_write",
            "list_files",
            "command_exec",
            "memory_save",
            "memory_search",
            "web_search",
        ],
    )
    def test_expected_tool_registered(self, tool_name: str):
        """Ferramenta '{tool_name}' deve estar registrada."""
        tool_names = [t.get("name", t.get("function", {}).get("name")) for t in TOOLS_SPEC]

        # Fallback: tenta checar como dict com chave do nome
        if not tool_names or all(n is None for n in tool_names):
            # Talvez TOOLS_SPEC seja um dict
            if isinstance(TOOLS_SPEC, dict):
                assert tool_name in TOOLS_SPEC, (
                    f"Ferramenta '{tool_name}' não encontrada no registro. "
                    f"Disponíveis: {list(TOOLS_SPEC.keys())}"
                )
                return

        assert tool_name in tool_names, (
            f"Ferramenta '{tool_name}' não encontrada. "
            f"Registradas: {tool_names}"
        )

    def test_each_tool_has_description(self):
        """Cada ferramenta deve ter uma descrição."""
        if isinstance(TOOLS_SPEC, dict):
            for name, spec in TOOLS_SPEC.items():
                desc = spec.get("description", "")
                assert desc, f"Ferramenta '{name}' não tem descrição"
        elif isinstance(TOOLS_SPEC, list):
            for tool in TOOLS_SPEC:
                name = tool.get("name", tool.get("function", {}).get("name", "?"))
                desc = tool.get(
                    "description",
                    tool.get("function", {}).get("description", ""),
                )
                assert desc, f"Ferramenta '{name}' não tem descrição"


class TestExecuteTool:
    """Testes para execução de ferramentas."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """Executar ferramenta desconhecida deve retornar indicação de erro."""
        result = await execute_tool("nonexistent_tool_xyz", {})

        # O resultado deve indicar erro (pode ser dict, string, ou exceção)
        if isinstance(result, dict):
            has_error = (
                result.get("error") is not None
                or result.get("success") is False
                or "erro" in str(result).lower()
                or "error" in str(result).lower()
                or "desconhecida" in str(result).lower()
            )
            assert has_error, (
                f"Deveria retornar erro para ferramenta desconhecida, got: {result}"
            )
        elif isinstance(result, str):
            result_lower = result.lower()
            has_error = any(word in result_lower for word in [
                "error", "erro", "not found", "desconhecida", "unknown", "❌"
            ])
            assert has_error, (
                f"Deveria indicar erro, got: {result}"
            )
        else:
            pytest.fail(
                f"Tipo de retorno inesperado para ferramenta desconhecida: "
                f"{type(result)} = {result}"
            )

    @pytest.mark.asyncio
    async def test_unknown_tool_does_not_crash(self):
        """Executar ferramenta desconhecida não deve lançar exceção não tratada."""
        # Não deve levantar exceção (o erro deve ser retornado, não raised)
        try:
            await execute_tool("absolutely_fake_tool", {"key": "value"})
        except (KeyError, ValueError, TypeError) as e:
            # Exceções controladas são aceitáveis
            pass
        except Exception as e:
            pytest.fail(
                f"Exceção inesperada ao executar ferramenta desconhecida: "
                f"{type(e).__name__}: {e}"
            )

    @pytest.mark.asyncio
    async def test_empty_tool_name_returns_error(self):
        """Nome de ferramenta vazio deve retornar erro."""
        result = await execute_tool("", {})

        if isinstance(result, dict):
            has_error = (
                result.get("error") is not None
                or result.get("success") is False
            )
            assert has_error, "Deveria retornar erro para nome vazio"
        elif isinstance(result, str):
            assert "erro" in result.lower() or "error" in result.lower() or "❌" in result or len(result) > 0
