"""Testes para memory_list e plans_spec."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from denai.tools.memory import memory_list

# ─── Helpers ───────────────────────────────────────────────────────────────


def _seed_memories(db_path: Path, entries: list[dict]) -> None:
    """Insere memórias diretamente no banco."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'observation',
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_memories_content ON memories(content)""")
    for e in entries:
        conn.execute(
            "INSERT INTO memories (type, content, tags, created_at) VALUES (?, ?, ?, ?)",
            (e.get("type", "observation"), e["content"], e.get("tags", ""), e.get("created_at", "2026-01-01T00:00:00")),
        )
    conn.commit()
    conn.close()


# ─── memory_list ───────────────────────────────────────────────────────────


class TestMemoryList:
    @pytest.mark.asyncio
    async def test_empty_returns_no_memories_message(self, tmp_path):
        db = tmp_path / "memory.db"
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({})
        assert "Nenhuma" in result

    @pytest.mark.asyncio
    async def test_lists_all_memories(self, tmp_path):
        db = tmp_path / "memory.db"
        _seed_memories(
            db,
            [
                {"type": "fact", "content": "Python é top", "tags": "python"},
                {"type": "decision", "content": "Usar SQLite", "tags": "db"},
                {"type": "observation", "content": "Bug no parser", "tags": ""},
            ],
        )
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({})
        assert "3 de 3" in result
        assert "Python é top" in result
        assert "Usar SQLite" in result
        assert "Bug no parser" in result

    @pytest.mark.asyncio
    async def test_filter_by_type(self, tmp_path):
        db = tmp_path / "memory.db"
        _seed_memories(
            db,
            [
                {"type": "fact", "content": "Fato 1", "tags": ""},
                {"type": "fact", "content": "Fato 2", "tags": ""},
                {"type": "decision", "content": "Decisão X", "tags": ""},
            ],
        )
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({"type": "fact"})
        assert "Fato 1" in result
        assert "Fato 2" in result
        assert "Decisão X" not in result

    @pytest.mark.asyncio
    async def test_limit_respected(self, tmp_path):
        db = tmp_path / "memory.db"
        entries = [{"type": "observation", "content": f"Obs {i}", "tags": ""} for i in range(30)]
        _seed_memories(db, entries)
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({"limit": 5})
        # Deve informar 5 de 30
        assert "5 de 30" in result

    @pytest.mark.asyncio
    async def test_limit_capped_at_50(self, tmp_path):
        db = tmp_path / "memory.db"
        entries = [{"type": "observation", "content": f"Obs {i}", "tags": ""} for i in range(60)]
        _seed_memories(db, entries)
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({"limit": 100})
        # Max é 50
        assert "50 de 60" in result

    @pytest.mark.asyncio
    async def test_shows_type_icons(self, tmp_path):
        db = tmp_path / "memory.db"
        _seed_memories(
            db,
            [
                {"type": "fact", "content": "Fato", "tags": ""},
                {"type": "preference", "content": "Preferência", "tags": ""},
            ],
        )
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({})
        assert "📌" in result  # fact
        assert "💜" in result  # preference

    @pytest.mark.asyncio
    async def test_default_limit_is_20(self, tmp_path):
        db = tmp_path / "memory.db"
        entries = [{"type": "observation", "content": f"Obs {i}", "tags": ""} for i in range(25)]
        _seed_memories(db, entries)
        with patch("denai.tools.memory.MEMORY_DB", db):
            result = await memory_list({})
        assert "20 de 25" in result

    @pytest.mark.asyncio
    async def test_memory_list_is_registered_as_tool(self):
        from denai.tools.memory import TOOLS

        names = [name for _, name in TOOLS]
        assert "memory_list" in names


# ─── plans_spec ────────────────────────────────────────────────────────────


@pytest.fixture
def plans_env(tmp_path):
    """Configura ambiente isolado para plans_spec."""
    plans_dir = tmp_path / "plans"
    plans_trash = plans_dir / ".trash"
    plans_dir.mkdir()
    plans_trash.mkdir()
    db_path = tmp_path / "plan_specs.db"

    with (
        patch("denai.tools.plans_spec.PLANS_DIR", plans_dir),
        patch("denai.tools.plans_spec.PLANS_TRASH_DIR", plans_trash),
        patch("denai.tools.plans_spec.PLANS_DB", db_path),
    ):
        yield {"dir": plans_dir, "trash": plans_trash, "db": db_path}


class TestPlansSpecCreate:
    @pytest.mark.asyncio
    async def test_create_basic(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "create", "title": "Minha Feature", "content": "# Plano\nDetalhes aqui."})
        assert "✅" in result
        assert "minha-feature" in result

    @pytest.mark.asyncio
    async def test_create_requires_title(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "create", "content": "Conteúdo"})
        assert "❌" in result
        assert "title" in result

    @pytest.mark.asyncio
    async def test_create_requires_content(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "create", "title": "Algo"})
        assert "❌" in result
        assert "content" in result

    @pytest.mark.asyncio
    async def test_create_persists_md_file(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Test File", "content": "# Hello"})
        md_files = list(plans_env["dir"].glob("*.md"))
        assert len(md_files) == 1
        assert md_files[0].read_text() == "# Hello"

    @pytest.mark.asyncio
    async def test_create_default_status_is_draft(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Draft Test", "content": "x"})
        conn = _get_db()
        row = conn.execute("SELECT status FROM plan_specs WHERE title = 'Draft Test'").fetchone()
        conn.close()
        assert row["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_with_active_status(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Active Plan", "content": "x", "status": "active"})
        conn = _get_db()
        row = conn.execute("SELECT status FROM plan_specs WHERE title = 'Active Plan'").fetchone()
        conn.close()
        assert row["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_unique_ids_for_same_title(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Duplicado", "content": "x"})
        await plans_spec({"action": "create", "title": "Duplicado", "content": "y"})
        conn = _get_db()
        rows = conn.execute("SELECT id FROM plan_specs").fetchall()
        conn.close()
        ids = [r["id"] for r in rows]
        assert len(set(ids)) == 2

    @pytest.mark.asyncio
    async def test_create_with_tags(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Tagged", "content": "x", "tags": "denai,feature"})
        conn = _get_db()
        row = conn.execute("SELECT tags FROM plan_specs WHERE title = 'Tagged'").fetchone()
        conn.close()
        assert row["tags"] == "denai,feature"


class TestPlansSpecGet:
    @pytest.mark.asyncio
    async def test_get_returns_content(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Get Test", "content": "# Conteúdo\nDetalhes."})
        result = await plans_spec({"action": "get", "id": "get-test"})
        assert "# Conteúdo" in result
        assert "Get Test" in result

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "get", "id": "nao-existe"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_get_requires_id(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "get"})
        assert "❌" in result


class TestPlansSpecList:
    @pytest.mark.asyncio
    async def test_list_empty(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "list"})
        assert "Nenhum" in result

    @pytest.mark.asyncio
    async def test_list_shows_all(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Plano A", "content": "a"})
        await plans_spec({"action": "create", "title": "Plano B", "content": "b"})
        result = await plans_spec({"action": "list"})
        assert "Plano A" in result
        assert "Plano B" in result
        assert "2 spec(s)" in result

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Ativo", "content": "a", "status": "active"})
        await plans_spec({"action": "create", "title": "Rascunho", "content": "b", "status": "draft"})
        result = await plans_spec({"action": "list", "status": "active"})
        assert "Ativo" in result
        assert "Rascunho" not in result


class TestPlansSpecUpdate:
    @pytest.mark.asyncio
    async def test_update_status(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Update Me", "content": "x"})
        result = await plans_spec({"action": "update", "id": "update-me", "status": "done"})
        assert "✅" in result
        conn = _get_db()
        row = conn.execute("SELECT status FROM plan_specs WHERE id = 'update-me'").fetchone()
        conn.close()
        assert row["status"] == "done"

    @pytest.mark.asyncio
    async def test_update_content(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Content Update", "content": "old"})
        await plans_spec({"action": "update", "id": "content-update", "content": "new content"})
        result = await plans_spec({"action": "get", "id": "content-update"})
        assert "new content" in result

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "update", "id": "ghost", "status": "done"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_update_invalid_status(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Bad Status", "content": "x"})
        result = await plans_spec({"action": "update", "id": "bad-status", "status": "invalid"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_update_requires_id(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "update", "status": "done"})
        assert "❌" in result


class TestPlansSpecDelete:
    @pytest.mark.asyncio
    async def test_delete_moves_to_trash(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        await plans_spec({"action": "create", "title": "Delete Me", "content": "bye"})
        result = await plans_spec({"action": "delete", "id": "delete-me"})
        assert "🗑️" in result
        assert (plans_env["trash"] / "delete-me.md").exists()
        assert not (plans_env["dir"] / "delete-me.md").exists()

    @pytest.mark.asyncio
    async def test_delete_removes_from_db(self, plans_env):
        from denai.tools.plans_spec import _get_db, plans_spec

        await plans_spec({"action": "create", "title": "Gone", "content": "x"})
        await plans_spec({"action": "delete", "id": "gone"})
        conn = _get_db()
        row = conn.execute("SELECT * FROM plan_specs WHERE id = 'gone'").fetchone()
        conn.close()
        assert row is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "delete", "id": "phantom"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_delete_requires_id(self, plans_env):
        from denai.tools.plans_spec import plans_spec

        result = await plans_spec({"action": "delete"})
        assert "❌" in result


class TestPlansSpecToolRegistration:
    def test_plans_spec_registered(self):
        from denai.tools.plans_spec import TOOLS

        names = [name for _, name in TOOLS]
        assert "plans_spec" in names

    def test_plans_spec_in_registry(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "plans_spec" in names

    def test_memory_list_in_registry(self):
        from denai.tools.registry import TOOLS_SPEC

        names = [t.get("function", {}).get("name") for t in TOOLS_SPEC]
        assert "memory_list" in names


class TestSlugify:
    def test_basic_slug(self):
        from denai.tools.plans_spec import _slugify

        assert _slugify("Minha Feature") == "minha-feature"

    def test_accented_chars(self):
        from denai.tools.plans_spec import _slugify

        assert _slugify("Configuração Geral") == "configuracao-geral"

    def test_multiple_spaces(self):
        from denai.tools.plans_spec import _slugify

        assert _slugify("  Muitos   Espaços  ") == "muitos-espacos"

    def test_special_chars_removed(self):
        from denai.tools.plans_spec import _slugify

        assert _slugify("Hello! World?") == "hello-world"

    def test_truncated_at_80(self):
        from denai.tools.plans_spec import _slugify

        long_title = "a" * 100
        assert len(_slugify(long_title)) <= 80
