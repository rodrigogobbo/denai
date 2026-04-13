"""Testes para context_store e rotas de contexto."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from denai.context_store import (
    activate_context,
    deactivate_context,
    get_context,
    has_context,
    search_context,
)

# ─── context_store ─────────────────────────────────────────────────────────


class TestActivateContext:
    def test_activate_valid_directory(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Test Project")

        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(
                path=str(tmp_path),
                name="test-project",
                languages=["Python"],
                file_count=2,
            )
            result = activate_context("conv-1", str(tmp_path))

        assert result["ok"] is True
        assert result["project_name"] == "test-project"
        assert result["file_count"] >= 1

    def test_activate_invalid_path(self, tmp_path):
        with patch("denai.context_store.is_path_allowed", return_value=(False, "fora do home")):
            result = activate_context("conv-2", "/etc/passwd")
        assert result["ok"] is False
        assert "não permitido" in result["error"]

    def test_activate_non_directory(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        with patch("denai.context_store.is_path_allowed", return_value=(True, "")):
            result = activate_context("conv-3", str(f))
        assert result["ok"] is False
        assert "diretório" in result["error"]

    def test_activate_persists_in_store(self, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="proj")
            activate_context("conv-4", str(tmp_path))

        assert has_context("conv-4") is True
        ctx = get_context("conv-4")
        assert ctx is not None
        assert ctx["project_name"] == "proj"

    def test_replaces_existing_context(self, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="first")
            activate_context("conv-5", str(tmp_path))
            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="second")
            activate_context("conv-5", str(tmp_path))

        assert get_context("conv-5")["project_name"] == "second"


class TestDeactivateContext:
    def test_deactivate_existing(self, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="proj")
            activate_context("conv-6", str(tmp_path))

        result = deactivate_context("conv-6")
        assert result is True
        assert has_context("conv-6") is False

    def test_deactivate_nonexistent(self):
        result = deactivate_context("nonexistent-conv")
        assert result is False


class TestSearchContext:
    def test_search_empty_when_no_context(self):
        results = search_context("no-conv", "anything")
        assert results == []

    def test_search_finds_relevant_file(self, tmp_path):
        (tmp_path / "auth.py").write_text("def login(user, password): pass\ndef logout(): pass")
        (tmp_path / "models.py").write_text("class User: pass\nclass Post: pass")

        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="proj")
            activate_context("conv-search", str(tmp_path))

        results = search_context("conv-search", "login password")
        paths = [r["path"] for r in results]
        assert any("auth" in p for p in paths)
        # Limpar
        deactivate_context("conv-search")


# ─── Routes ────────────────────────────────────────────────────────────────


@pytest.fixture
async def client(tmp_path):
    import aiosqlite

    from denai.app import create_app
    from denai.db import SCHEMA_SQL

    db_path = tmp_path / "test.db"
    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.config.DATA_DIR", tmp_path),
    ):
        _app = create_app()
        from denai.security.auth import API_KEY
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as c:
            yield c


class TestContextRoutes:
    @pytest.mark.asyncio
    async def test_activate_returns_ok(self, client, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="myproject")
            resp = await client.post(
                "/api/context/activate",
                json={
                    "path": str(tmp_path),
                    "conversation_id": "test-conv-123",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["project_name"] == "myproject"

    @pytest.mark.asyncio
    async def test_activate_bad_path_returns_400(self, client):
        with patch("denai.context_store.is_path_allowed", return_value=(False, "fora do home")):
            resp = await client.post(
                "/api/context/activate",
                json={
                    "path": "/etc/passwd",
                    "conversation_id": "test-conv-456",
                },
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_active_context(self, client, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="myproj")
            await client.post(
                "/api/context/activate",
                json={
                    "path": str(tmp_path),
                    "conversation_id": "get-ctx-conv",
                },
            )
        resp = await client.get("/api/context/get-ctx-conv")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True
        assert data["project_name"] == "myproj"

    @pytest.mark.asyncio
    async def test_get_inactive_context(self, client):
        resp = await client.get("/api/context/nonexistent-conv-xyz")
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    @pytest.mark.asyncio
    async def test_deactivate_context(self, client, tmp_path):
        with (
            patch("denai.context_store.is_path_allowed", return_value=(True, "")),
            patch("denai.context_store.analyze_project") as mock_analyze,
        ):
            from denai.project import ProjectInfo

            mock_analyze.return_value = ProjectInfo(path=str(tmp_path), name="p")
            await client.post(
                "/api/context/activate",
                json={
                    "path": str(tmp_path),
                    "conversation_id": "del-conv",
                },
            )
        resp = await client.delete("/api/context/del-conv")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Verificar que foi removido
        resp2 = await client.get("/api/context/del-conv")
        assert resp2.json()["active"] is False
