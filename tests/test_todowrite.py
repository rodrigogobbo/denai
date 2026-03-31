"""Testes para todowrite e todoread."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from denai.tools.todowrite import todoread, todowrite

# ─── Helpers ───────────────────────────────────────────────────────────────


def _read_db(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM todos ORDER BY rowid").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── todowrite ─────────────────────────────────────────────────────────────


class TestTodowrite:
    @pytest.mark.asyncio
    async def test_create_basic_list(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {
                    "todos": [
                        {"id": "1", "content": "Fazer X", "status": "pending"},
                        {"id": "2", "content": "Fazer Y", "status": "pending"},
                    ]
                }
            )
        assert "Fazer X" in result
        assert "Fazer Y" in result
        assert "0/2" in result

    @pytest.mark.asyncio
    async def test_replaces_entire_list(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite({"todos": [{"id": "1", "content": "Antigo", "status": "pending"}]})
            await todowrite(
                {
                    "todos": [
                        {"id": "a", "content": "Novo A", "status": "pending"},
                        {"id": "b", "content": "Novo B", "status": "in_progress"},
                    ]
                }
            )
        rows = _read_db(db)
        assert len(rows) == 2
        ids = [r["id"] for r in rows]
        assert "1" not in ids
        assert "a" in ids
        assert "b" in ids

    @pytest.mark.asyncio
    async def test_status_completed_counts(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {
                    "todos": [
                        {"id": "1", "content": "Feito", "status": "completed"},
                        {"id": "2", "content": "Pendente", "status": "pending"},
                        {"id": "3", "content": "Em andamento", "status": "in_progress"},
                    ]
                }
            )
        assert "1/3" in result

    @pytest.mark.asyncio
    async def test_all_completed(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {
                    "todos": [
                        {"id": "1", "content": "A", "status": "completed"},
                        {"id": "2", "content": "B", "status": "completed"},
                    ]
                }
            )
        assert "2/2" in result

    @pytest.mark.asyncio
    async def test_priority_default_is_medium(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite({"todos": [{"id": "1", "content": "Sem prioridade", "status": "pending"}]})
        rows = _read_db(db)
        assert rows[0]["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_priority_high_shows_icon(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {"todos": [{"id": "1", "content": "Urgente", "status": "pending", "priority": "high"}]}
            )
        assert "🔴" in result

    @pytest.mark.asyncio
    async def test_priority_low_shows_icon(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {"todos": [{"id": "1", "content": "Baixo", "status": "pending", "priority": "low"}]}
            )
        assert "🔵" in result

    @pytest.mark.asyncio
    async def test_invalid_priority_defaults_to_medium(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite({"todos": [{"id": "1", "content": "X", "status": "pending", "priority": "super-high"}]})
        rows = _read_db(db)
        assert rows[0]["priority"] == "medium"

    @pytest.mark.asyncio
    async def test_empty_list_clears(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite({"todos": [{"id": "1", "content": "X", "status": "pending"}]})
            result = await todowrite({"todos": []})
        assert "vazia" in result
        assert len(_read_db(db)) == 0

    @pytest.mark.asyncio
    async def test_duplicate_ids_rejected(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {
                    "todos": [
                        {"id": "dup", "content": "A", "status": "pending"},
                        {"id": "dup", "content": "B", "status": "pending"},
                    ]
                }
            )
        assert "❌" in result
        assert "dup" in result

    @pytest.mark.asyncio
    async def test_missing_id_rejected(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite({"todos": [{"content": "Sem ID", "status": "pending"}]})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_missing_content_rejected(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite({"todos": [{"id": "1", "status": "pending"}]})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite({"todos": [{"id": "1", "content": "X", "status": "flying"}]})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_todos_not_a_list(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite({"todos": "não é lista"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_status_icons_displayed(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {
                    "todos": [
                        {"id": "1", "content": "Pendente", "status": "pending"},
                        {"id": "2", "content": "Em andamento", "status": "in_progress"},
                        {"id": "3", "content": "Concluído", "status": "completed"},
                    ]
                }
            )
        assert "⬜" in result
        assert "🔄" in result
        assert "✅" in result

    @pytest.mark.asyncio
    async def test_ids_shown_in_output(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todowrite(
                {"todos": [{"id": "setup-db", "content": "Configurar banco", "status": "pending"}]}
            )
        assert "setup-db" in result

    @pytest.mark.asyncio
    async def test_persists_order(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite(
                {
                    "todos": [
                        {"id": "c", "content": "C", "status": "pending"},
                        {"id": "a", "content": "A", "status": "pending"},
                        {"id": "b", "content": "B", "status": "pending"},
                    ]
                }
            )
        rows = _read_db(db)
        assert [r["id"] for r in rows] == ["c", "a", "b"]


# ─── todoread ──────────────────────────────────────────────────────────────


class TestTodoread:
    @pytest.mark.asyncio
    async def test_read_empty(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            result = await todoread({})
        assert "vazia" in result

    @pytest.mark.asyncio
    async def test_read_after_write(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite(
                {
                    "todos": [
                        {"id": "1", "content": "Tarefa A", "status": "in_progress"},
                        {"id": "2", "content": "Tarefa B", "status": "pending"},
                    ]
                }
            )
            result = await todoread({})
        assert "Tarefa A" in result
        assert "Tarefa B" in result
        assert "0/2" in result

    @pytest.mark.asyncio
    async def test_read_reflects_latest_write(self, tmp_path):
        db = tmp_path / "todos.db"
        with patch("denai.tools.todowrite.TODOS_DB", db):
            await todowrite({"todos": [{"id": "1", "content": "Antiga", "status": "pending"}]})
            await todowrite({"todos": [{"id": "x", "content": "Nova", "status": "completed"}]})
            result = await todoread({})
        assert "Nova" in result
        assert "Antiga" not in result
        assert "1/1" in result


# ─── Registration ──────────────────────────────────────────────────────────


class TestTodoRegistration:
    def test_todowrite_registered(self):
        from denai.tools.todowrite import TOOLS

        names = [name for _, name in TOOLS]
        assert "todowrite" in names
        assert "todoread" in names

    def test_todowrite_in_registry(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "todowrite" in names
        assert "todoread" in names

    def test_todoread_in_plan_mode(self):
        from denai.modes import PLAN_MODE_TOOLS

        assert "todoread" in PLAN_MODE_TOOLS

    def test_todowrite_not_in_plan_mode(self):
        from denai.modes import PLAN_MODE_TOOLS

        assert "todowrite" not in PLAN_MODE_TOOLS
