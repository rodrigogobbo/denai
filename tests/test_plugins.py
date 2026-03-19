"""Testes para o sistema de plugins do DenAI."""

import json
from unittest.mock import patch

# ── Plugin Loading ──────────────────────────────────────────────────────


class TestPluginDiscovery:
    """Testes para descoberta de plugins em ~/.denai/plugins/."""

    def test_discover_empty_dir(self, tmp_path):
        """Sem plugins, retorna lista vazia."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins

            result = discover_plugins()
            assert result == []

    def test_discover_single_file_plugin(self, tmp_path):
        """Descobre plugin de arquivo único (.py)."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_file = plugins_dir / "hello.py"
        plugin_file.write_text('''
"""Plugin de teste: hello."""

__version__ = "1.0.0"

SPEC = {
    "type": "function",
    "function": {
        "name": "hello",
        "description": "Says hello.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    },
}

async def hello(args):
    return f"Hello, {args.get('name', 'world')}!"

TOOLS = [(SPEC, "hello")]
''')

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins

            result = discover_plugins()

        assert len(result) == 1
        assert result[0]["name"] == "hello"
        assert result[0]["status"] == "loaded"
        assert result[0]["version"] == "1.0.0"
        assert len(result[0]["tools"]) == 1

    def test_discover_directory_plugin(self, tmp_path):
        """Descobre plugin de diretório (plugin.json + main.py)."""
        plugins_dir = tmp_path / "plugins"
        plugin_dir = plugins_dir / "my_plugin"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "plugin.json").write_text(
            json.dumps({"name": "My Plugin", "version": "2.0.0", "description": "Test plugin"})
        )

        (plugin_dir / "main.py").write_text("""
SPEC = {
    "type": "function",
    "function": {
        "name": "greet",
        "description": "Greets.",
        "parameters": {"type": "object", "properties": {}},
    },
}

async def greet(args):
    return "Hi!"

TOOLS = [(SPEC, "greet")]
""")

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins

            result = discover_plugins()

        assert len(result) == 1
        assert result[0]["name"] == "My Plugin"
        assert result[0]["version"] == "2.0.0"
        assert result[0]["type"] == "directory"

    def test_ignores_underscored_files(self, tmp_path):
        """Ignora arquivos e diretórios que começam com _."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "__init__.py").write_text("# ignored")
        (plugins_dir / "_helper.py").write_text("# ignored")

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins

            result = discover_plugins()
            assert result == []

    def test_broken_plugin_reports_error(self, tmp_path):
        """Plugin com erro de sintaxe reporta status 'error'."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "broken.py").write_text("def this is invalid syntax!!!")

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins

            result = discover_plugins()

        assert len(result) == 1
        assert result[0]["status"] == "error"
        assert result[0]["error"] is not None

    def test_get_plugin_tools_returns_specs_and_executors(self, tmp_path):
        """get_plugin_tools retorna specs e executors de plugins carregados."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "calc.py").write_text("""
SPEC = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Adds numbers.",
        "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}},
    },
}

async def add(args):
    return str(args.get("a", 0) + args.get("b", 0))

TOOLS = [(SPEC, "add")]
""")

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins, get_plugin_tools

            discover_plugins()
            specs, executors = get_plugin_tools()

        assert len(specs) == 1
        assert specs[0]["function"]["name"] == "add"
        assert "add" in executors

    def test_list_plugins_excludes_executors(self, tmp_path):
        """list_plugins retorna metadados sem executors (serializable)."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "simple.py").write_text("""
SPEC = {"type": "function", "function": {"name": "noop", "description": "No-op", "parameters": {"type": "object"}}}
async def noop(args): return "ok"
TOOLS = [(SPEC, "noop")]
""")

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins, list_plugins

            discover_plugins()
            plugins = list_plugins()

        assert len(plugins) == 1
        assert "executors" not in plugins[0]
        assert "name" in plugins[0]
        assert "tools_count" in plugins[0]
        assert plugins[0]["tools_count"] == 1

    def test_no_plugins_dir_returns_empty(self, tmp_path):
        """Se diretório de plugins não existe, retorna vazio sem erro."""
        nonexistent = tmp_path / "nonexistent_plugins"

        with patch("denai.plugins.PLUGINS_DIR", nonexistent):
            from denai.plugins import discover_plugins

            result = discover_plugins()
            assert result == []


class TestPluginExecution:
    """Testa execução de funções de plugins."""

    async def test_plugin_executor_works(self, tmp_path):
        """Executor de plugin funciona via execute_tool."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        (plugins_dir / "echo.py").write_text(
            'SPEC = {"type": "function", "function": {"name": "echo_test", '
            '"description": "Echo", "parameters": {"type": "object", '
            '"properties": {"msg": {"type": "string"}}}}}\n\n'
            "async def echo_test(args):\n"
            "    return f\"Echo: {args.get('msg', '')}\"\n\n"
            'TOOLS = [(SPEC, "echo_test")]\n'
        )

        with patch("denai.plugins.PLUGINS_DIR", plugins_dir):
            from denai.plugins import discover_plugins, get_plugin_tools

            discover_plugins()
            _, executors = get_plugin_tools()

            assert "echo_test" in executors
            result = await executors["echo_test"]({"msg": "test"})
            assert result == "Echo: test"
