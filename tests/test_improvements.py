"""Testes para as melhorias: grep, think, planning persistido, file backup, retry/recovery."""

from __future__ import annotations

import json
import sqlite3
from unittest.mock import patch

import pytest

# ═══════════════════════════════════════════════════════════════════════════
# GREP TOOL
# ═══════════════════════════════════════════════════════════════════════════


class TestGrep:
    """Testes para a tool grep."""

    @pytest.mark.asyncio
    async def test_grep_finds_pattern(self, tmp_path):
        """Deve encontrar padrão em arquivo."""
        from denai.tools.grep import grep

        (tmp_path / "hello.py").write_text("def hello():\n    print('world')\n")
        (tmp_path / "bye.py").write_text("def goodbye():\n    pass\n")

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "def hello", "path": str(tmp_path)})

        assert "hello.py" in result
        assert "def hello" in result
        assert "1 resultado" in result

    @pytest.mark.asyncio
    async def test_grep_no_results(self, tmp_path):
        """Deve retornar mensagem quando não encontra nada."""
        from denai.tools.grep import grep

        (tmp_path / "empty.py").write_text("pass\n")

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "inexistente", "path": str(tmp_path)})

        assert "Nenhum resultado" in result

    @pytest.mark.asyncio
    async def test_grep_with_include_filter(self, tmp_path):
        """Deve filtrar por extensão."""
        from denai.tools.grep import grep

        (tmp_path / "code.py").write_text("import os\n")
        (tmp_path / "notes.txt").write_text("import os\n")

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "import os", "path": str(tmp_path), "include": "*.py"})

        assert "code.py" in result
        assert "notes.txt" not in result

    @pytest.mark.asyncio
    async def test_grep_invalid_regex(self, tmp_path):
        """Deve retornar erro para regex inválido."""
        from denai.tools.grep import grep

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "[invalid", "path": str(tmp_path)})

        assert "❌" in result
        assert "inválido" in result.lower() or "Regex" in result

    @pytest.mark.asyncio
    async def test_grep_missing_pattern(self):
        """Deve exigir pattern."""
        from denai.tools.grep import grep

        result = await grep({})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_grep_respects_max_results(self, tmp_path):
        """Deve limitar resultados."""
        from denai.tools.grep import grep

        content = "\n".join(f"match line {i}" for i in range(100))
        (tmp_path / "big.txt").write_text(content)

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "match", "path": str(tmp_path), "max_results": 5})

        assert "limitado a 5" in result

    @pytest.mark.asyncio
    async def test_grep_skips_pycache(self, tmp_path):
        """Deve ignorar __pycache__."""
        from denai.tools.grep import grep

        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("match this\n")
        (tmp_path / "real.py").write_text("match this\n")

        with patch("denai.tools.grep.is_path_allowed", return_value=(True, "")):
            result = await grep({"pattern": "match", "path": str(tmp_path)})

        assert "real.py" in result
        assert "__pycache__" not in result

    @pytest.mark.asyncio
    async def test_grep_sandbox_block(self):
        """Deve respeitar sandbox."""
        from denai.tools.grep import grep

        result = await grep({"pattern": "test", "path": "/etc"})
        assert "🔒" in result or "negado" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# THINK TOOL
# ═══════════════════════════════════════════════════════════════════════════


class TestThink:
    """Testes para a tool think."""

    @pytest.mark.asyncio
    async def test_think_returns_thought(self):
        """Deve retornar o pensamento sem side effects."""
        from denai.tools.think import think

        result = await think({"thought": "Preciso ler o arquivo antes de editar"})
        assert "💭" in result
        assert "Preciso ler o arquivo" in result

    @pytest.mark.asyncio
    async def test_think_empty(self):
        """Deve exigir thought."""
        from denai.tools.think import think

        result = await think({"thought": ""})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_think_missing_param(self):
        """Deve exigir parâmetro."""
        from denai.tools.think import think

        result = await think({})
        assert "❌" in result


# ═══════════════════════════════════════════════════════════════════════════
# PLANNING PERSISTIDO
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanningPersisted:
    """Testes para planning com SQLite."""

    @pytest.mark.asyncio
    async def test_plan_create_persists(self, tmp_path):
        """Plano deve ser salvo no SQLite."""
        from denai.tools import planning

        # Redirecionar DB para tmp
        original_db = planning.PLANS_DB
        planning.PLANS_DB = tmp_path / "plans.db"
        try:
            result = await planning.plan_create(
                {
                    "goal": "Testar persistência",
                    "steps": ["Passo 1", "Passo 2"],
                }
            )
            assert "📋" in result
            assert "Testar persistência" in result

            # Verificar que está no SQLite
            conn = sqlite3.connect(str(tmp_path / "plans.db"))
            row = conn.execute("SELECT * FROM plans ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            assert row is not None
            assert "Testar persistência" in row[1]  # goal
        finally:
            planning.PLANS_DB = original_db

    @pytest.mark.asyncio
    async def test_plan_update_persists(self, tmp_path):
        """Update deve ser salvo no SQLite."""
        from denai.tools import planning

        original_db = planning.PLANS_DB
        planning.PLANS_DB = tmp_path / "plans.db"
        try:
            await planning.plan_create(
                {
                    "goal": "Test update",
                    "steps": ["Passo A", "Passo B"],
                }
            )
            result = await planning.plan_update(
                {
                    "step": 1,
                    "status": "done",
                    "result": "Concluído!",
                }
            )
            assert "✅" in result
            assert "Concluído!" in result

            # Verificar no DB
            conn = sqlite3.connect(str(tmp_path / "plans.db"))
            row = conn.execute("SELECT steps FROM plans ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            steps = json.loads(row[0])
            assert steps[0]["status"] == "done"
            assert steps[0]["result"] == "Concluído!"
        finally:
            planning.PLANS_DB = original_db

    @pytest.mark.asyncio
    async def test_plan_survives_reload(self, tmp_path):
        """Plano deve sobreviver a 'reinicialização'."""
        from denai.tools import planning

        original_db = planning.PLANS_DB
        planning.PLANS_DB = tmp_path / "plans.db"
        try:
            await planning.plan_create(
                {
                    "goal": "Sobreviver restart",
                    "steps": ["Única etapa"],
                }
            )
            # Simular "restart" limpando cache e relendo
            plan = planning._get_current_plan()
            assert plan is not None
            assert plan["goal"] == "Sobreviver restart"
        finally:
            planning.PLANS_DB = original_db

    @pytest.mark.asyncio
    async def test_plan_update_no_plan(self, tmp_path):
        """Update sem plano deve dar erro."""
        from denai.tools import planning

        original_db = planning.PLANS_DB
        planning.PLANS_DB = tmp_path / "empty_plans.db"
        try:
            result = await planning.plan_update({"step": 1, "status": "done"})
            assert "❌" in result
        finally:
            planning.PLANS_DB = original_db


# ═══════════════════════════════════════════════════════════════════════════
# FILE BACKUP
# ═══════════════════════════════════════════════════════════════════════════


class TestFileBackup:
    """Testes para backup automático de arquivos."""

    @pytest.mark.asyncio
    async def test_file_write_creates_backup(self, tmp_path):
        """file_write deve criar backup do arquivo existente."""
        from denai.tools import file_ops

        f = tmp_path / "original.txt"
        f.write_text("conteúdo original")

        backup_dir = tmp_path / "backups"
        original_backup_dir = file_ops.BACKUP_DIR
        file_ops.BACKUP_DIR = backup_dir

        try:
            with patch("denai.tools.file_ops.is_path_allowed", return_value=(True, "")):
                with patch("denai.tools.file_ops._resolve_path", return_value=f):
                    result = await file_ops.file_write({"path": str(f), "content": "novo conteúdo"})

            assert "✅" in result
            assert "Backup" in result
            # Verificar que backup foi criado
            backups = list(backup_dir.glob("*original.txt"))
            assert len(backups) == 1
            assert backups[0].read_text() == "conteúdo original"
        finally:
            file_ops.BACKUP_DIR = original_backup_dir

    @pytest.mark.asyncio
    async def test_file_write_new_file_no_backup(self, tmp_path):
        """file_write de arquivo novo não deve criar backup."""
        from denai.tools import file_ops

        f = tmp_path / "new_file.txt"

        backup_dir = tmp_path / "backups"
        original_backup_dir = file_ops.BACKUP_DIR
        file_ops.BACKUP_DIR = backup_dir

        try:
            with patch("denai.tools.file_ops.is_path_allowed", return_value=(True, "")):
                with patch("denai.tools.file_ops._resolve_path", return_value=f):
                    result = await file_ops.file_write({"path": str(f), "content": "novo"})

            assert "✅" in result
            assert "Backup" not in result
        finally:
            file_ops.BACKUP_DIR = original_backup_dir

    @pytest.mark.asyncio
    async def test_file_edit_creates_backup(self, tmp_path):
        """file_edit deve criar backup antes de editar."""
        from denai.tools import file_ops

        f = tmp_path / "to_edit.txt"
        f.write_text("hello world")

        backup_dir = tmp_path / "backups"
        original_backup_dir = file_ops.BACKUP_DIR
        file_ops.BACKUP_DIR = backup_dir

        try:
            with patch("denai.tools.file_ops.is_path_allowed", return_value=(True, "")):
                with patch("denai.tools.file_ops._resolve_path", return_value=f):
                    result = await file_ops.file_edit(
                        {
                            "path": str(f),
                            "old_text": "hello",
                            "new_text": "bye",
                        }
                    )

            assert "✅" in result
            # Verificar backup
            backups = list(backup_dir.glob("*to_edit.txt"))
            assert len(backups) == 1
            assert backups[0].read_text() == "hello world"
            # Verificar edição
            assert f.read_text() == "bye world"
        finally:
            file_ops.BACKUP_DIR = original_backup_dir


# ═══════════════════════════════════════════════════════════════════════════
# RECOVERY HINTS
# ═══════════════════════════════════════════════════════════════════════════


class TestRecoveryHints:
    """Testes para hints de recuperação de erro."""

    def test_file_edit_not_found_hint(self):
        """Deve gerar hint específico para file_edit."""
        from denai.llm.ollama import _build_recovery_hint

        hint = _build_recovery_hint("file_edit", "❌ Texto não encontrado no arquivo")
        assert "file_read" in hint
        assert "Dica" in hint

    def test_file_read_not_found_hint(self):
        """Deve gerar hint para arquivo inexistente."""
        from denai.llm.ollama import _build_recovery_hint

        hint = _build_recovery_hint("file_read", "❌ Arquivo não encontrado: /tmp/x")
        assert "list_files" in hint

    def test_command_permission_hint(self):
        """Deve gerar hint para erro de permissão."""
        from denai.llm.ollama import _build_recovery_hint

        hint = _build_recovery_hint("command_exec", "❌ Sem permissão para executar")
        assert "alternativa" in hint.lower()

    def test_security_block_hint(self):
        """Deve gerar hint para bloqueio de segurança."""
        from denai.llm.ollama import _build_recovery_hint

        hint = _build_recovery_hint("file_read", "🔒 Caminho bloqueado")
        assert "bloqueado" in hint.lower()

    def test_no_hint_for_unknown_error(self):
        """Erro genérico não deve gerar hint."""
        from denai.llm.ollama import _build_recovery_hint

        hint = _build_recovery_hint("file_read", "❌ Algum erro qualquer")
        assert hint == ""


# ═══════════════════════════════════════════════════════════════════════════
# WEB SEARCH (DuckDuckGo)
# ═══════════════════════════════════════════════════════════════════════════


class TestWebSearchDDG:
    """Testes para web_search com DuckDuckGo."""

    def test_is_url_detection(self):
        """Deve detectar URLs vs queries."""
        from denai.tools.web_fetch import _is_url

        assert _is_url("https://example.com") is True
        assert _is_url("http://example.com/page") is True
        assert _is_url("example.com") is True
        assert _is_url("como fazer X em Python") is False
        assert _is_url("o que é machine learning") is False

    @pytest.mark.asyncio
    async def test_web_search_url_backward_compat(self):
        """Deve aceitar parâmetro 'url' para retrocompatibilidade."""
        from denai.tools.web_fetch import web_search

        # URL interna = bloqueada, mas prova que aceita o parâmetro
        result = await web_search({"url": "http://127.0.0.1"})
        assert "🔒" in result

    @pytest.mark.asyncio
    async def test_web_search_empty_query(self):
        """Deve exigir query."""
        from denai.tools.web_fetch import web_search

        result = await web_search({})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_web_search_ssrf_blocked(self):
        """Deve bloquear URLs internas."""
        from denai.tools.web_fetch import web_search

        for url in ["http://127.0.0.1", "http://192.168.1.1", "http://localhost"]:
            result = await web_search({"query": url})
            assert "🔒" in result


# ═══════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    """Testes para o circuit breaker e transient error detection."""

    def test_transient_errors(self):
        """Deve classificar erros transientes."""
        from denai.llm.ollama import _is_transient_error

        assert _is_transient_error(429) is True
        assert _is_transient_error(500) is True
        assert _is_transient_error(502) is True
        assert _is_transient_error(503) is True
        assert _is_transient_error(504) is True
        assert _is_transient_error(400) is False
        assert _is_transient_error(404) is False
        assert _is_transient_error(200) is False


# ═══════════════════════════════════════════════════════════════════════════
# TOOL COUNT UPDATED
# ═══════════════════════════════════════════════════════════════════════════


class TestToolCount:
    """Verifica que as novas tools foram registradas."""

    def test_tools_include_grep(self):
        """grep deve estar registrada."""
        from denai.tools import TOOLS_SPEC

        names = [t["function"]["name"] for t in TOOLS_SPEC]
        assert "grep" in names

    def test_tools_include_think(self):
        """think deve estar registrada."""
        from denai.tools import TOOLS_SPEC

        names = [t["function"]["name"] for t in TOOLS_SPEC]
        assert "think" in names

    def test_total_tools_count(self):
        """Deve ter 16 tools (14 anteriores + grep + think)."""
        from denai.tools import TOOLS_SPEC

        assert len(TOOLS_SPEC) >= 16


# ─── Parallel tool batching tests ─────────────────────────────────────────


class TestToolBatching:
    """Tests for _batch_tool_calls parallel grouping."""

    def _make_tc(self, name):
        return {"function": {"name": name, "arguments": {}}}

    def test_single_tool(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        tcs = [self._make_tc("file_read")]
        batches = _batch_tool_calls(tcs, Counter())
        assert len(batches) == 1
        assert len(batches[0]) == 1

    def test_parallel_safe_grouped(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        tcs = [self._make_tc("file_read"), self._make_tc("grep"), self._make_tc("think")]
        batches = _batch_tool_calls(tcs, Counter())
        assert len(batches) == 1
        assert len(batches[0]) == 3

    def test_write_breaks_batch(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        tcs = [self._make_tc("file_read"), self._make_tc("file_write"), self._make_tc("grep")]
        batches = _batch_tool_calls(tcs, Counter())
        assert len(batches) == 3  # [file_read], [file_write], [grep]

    def test_all_write_sequential(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        tcs = [self._make_tc("file_write"), self._make_tc("file_edit"), self._make_tc("command_exec")]
        batches = _batch_tool_calls(tcs, Counter())
        assert len(batches) == 3  # each alone

    def test_mixed_batch(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        tcs = [
            self._make_tc("file_read"),
            self._make_tc("memory_search"),
            self._make_tc("file_write"),
            self._make_tc("grep"),
            self._make_tc("think"),
        ]
        batches = _batch_tool_calls(tcs, Counter())
        assert len(batches) == 3
        assert len(batches[0]) == 2  # file_read + memory_search
        assert len(batches[1]) == 1  # file_write
        assert len(batches[2]) == 2  # grep + think

    def test_circuit_breaker_breaks_parallel(self):
        from collections import Counter

        from denai.llm.ollama import CIRCUIT_BREAKER_LIMIT, _batch_tool_calls

        failures = Counter({"file_read": CIRCUIT_BREAKER_LIMIT})
        tcs = [self._make_tc("grep"), self._make_tc("file_read"), self._make_tc("think")]
        batches = _batch_tool_calls(tcs, failures)
        # file_read has circuit breaker → not parallel safe → breaks batch
        assert len(batches) == 3

    def test_empty_list(self):
        from collections import Counter

        from denai.llm.ollama import _batch_tool_calls

        assert _batch_tool_calls([], Counter()) == []
