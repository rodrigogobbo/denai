"""Testes para os endpoints de specs (/api/specs/*)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
    import aiosqlite

    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
    ):
        app = create_app()
        from denai.security.auth import API_KEY
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as c:
            yield c, tmp_path


def _make_specs_dir(base: Path) -> Path:
    """Cria estrutura de specs de exemplo."""
    specs_dir = base / "myproject" / "specs" / "changes"
    spec = specs_dir / "v1.0-feature"
    spec.mkdir(parents=True)
    (spec / "requirements.md").write_text("# Requirements\n\n- REQ-1: Feature X")
    (spec / "design.md").write_text("# Design\n\nDiagram here")
    (spec / "tasks.md").write_text("# Tasks\n\n- [x] TASK-1\n- [ ] TASK-2")
    return specs_dir


class TestSpecsList:
    """Testes para POST /api/specs/list."""

    @pytest.mark.asyncio
    async def test_list_no_context(self, client):
        c, _ = client
        with patch("denai.routes.specs.get_context", return_value=None):
            r = await c.post("/api/specs/list", json={"conversation_id": "abc"})
        assert r.status_code == 400
        assert "Nenhum repositório" in r.json()["error"]

    @pytest.mark.asyncio
    async def test_list_no_specs_dir(self, client, tmp_path):
        c, _ = client
        ctx = {"path": str(tmp_path / "no-specs"), "project_name": "test"}
        (tmp_path / "no-specs").mkdir()
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/list", json={"conversation_id": "abc"})
        assert r.status_code == 400
        assert "specs/changes" in r.json()["error"]

    @pytest.mark.asyncio
    async def test_list_with_specs(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/list", json={"conversation_id": "abc"})
        assert r.status_code == 200
        data = r.json()
        assert "v1.0-feature" in data["specs"]
        assert data["project"] == "myproject"

    @pytest.mark.asyncio
    async def test_list_empty_specs(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject2"
        specs_dir = project_dir / "specs" / "changes"
        specs_dir.mkdir(parents=True)
        ctx = {"path": str(project_dir), "project_name": "myproject2"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/list", json={"conversation_id": "abc"})
        assert r.status_code == 200
        data = r.json()
        assert data["specs"] == []


class TestSpecsRead:
    """Testes para POST /api/specs/read."""

    @pytest.mark.asyncio
    async def test_read_existing(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/read", json={"conversation_id": "abc", "slug": "v1.0-feature"})
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == "v1.0-feature"
        assert "requirements.md" in data["content"]
        assert "design.md" in data["content"]
        assert "tasks.md" in data["content"]

    @pytest.mark.asyncio
    async def test_read_not_found(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/read", json={"conversation_id": "abc", "slug": "nonexistent"})
        assert r.status_code == 404
        assert "não encontrada" in r.json()["error"]

    @pytest.mark.asyncio
    async def test_read_path_traversal(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/read", json={"conversation_id": "abc", "slug": "../../../etc"})
        # Deve retornar 404 (slug sanitizado não existe), não 200 com arquivo do sistema
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_read_no_context(self, client):
        c, _ = client
        with patch("denai.routes.specs.get_context", return_value=None):
            r = await c.post("/api/specs/read", json={"conversation_id": "abc", "slug": "test"})
        assert r.status_code == 400


class TestSpecsAnalyze:
    """Testes para POST /api/specs/analyze."""

    @pytest.mark.asyncio
    async def test_analyze_no_context(self, client):
        c, _ = client
        with patch("denai.routes.specs.get_context", return_value=None):
            r = await c.post("/api/specs/analyze", json={
                "conversation_id": "abc", "slug": "test", "model": "test-model"
            })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_analyze_not_found(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/analyze", json={
                "conversation_id": "abc", "slug": "nonexistent", "model": "test-model"
            })
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_streams(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}

        async def fake_stream(*args, **kwargs):
            yield f'data: {json.dumps({"content": "✅ TASK-1 concluída"})}\n\n'
            yield f'data: {json.dumps({"done": True})}\n\n'

        with (
            patch("denai.routes.specs.get_context", return_value=ctx),
            patch("denai.routes.specs.stream_chat", side_effect=fake_stream),
        ):
            r = await c.post("/api/specs/analyze", json={
                "conversation_id": "abc", "slug": "v1.0-feature", "model": "test-model"
            })

        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        # Primeiro chunk deve ter o slug
        chunks = [c.strip() for c in r.text.split("\n\n") if c.strip()]
        assert any("v1.0-feature" in c for c in chunks)

    @pytest.mark.asyncio
    async def test_analyze_path_traversal(self, client, tmp_path):
        c, _ = client
        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}
        with patch("denai.routes.specs.get_context", return_value=ctx):
            r = await c.post("/api/specs/analyze", json={
                "conversation_id": "abc", "slug": "../../etc/passwd", "model": "test-model"
            })
        assert r.status_code == 404


class TestSpecsAnalyzeTool:
    """Testes para a tool specs_analyze."""

    @pytest.mark.asyncio
    async def test_tool_no_context(self):
        from denai.tools.specs_analyzer import specs_analyze

        with patch("denai.tools.specs_analyzer.get_context", return_value=None):
            result = await specs_analyze({"slug": "test", "conversation_id": "abc"})
        assert "❌" in result
        assert "repositório" in result.lower()

    @pytest.mark.asyncio
    async def test_tool_missing_slug(self):
        from denai.tools.specs_analyzer import specs_analyze

        result = await specs_analyze({"conversation_id": "abc"})
        assert "❌" in result

    @pytest.mark.asyncio
    async def test_tool_reads_spec(self, tmp_path):
        from denai.tools.specs_analyzer import specs_analyze

        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}

        with patch("denai.tools.specs_analyzer.get_context", return_value=ctx):
            result = await specs_analyze({"slug": "v1.0-feature", "conversation_id": "abc"})

        assert "REQ-1" in result
        assert "TASK-1" in result
        assert "myproject" in result

    @pytest.mark.asyncio
    async def test_tool_path_traversal(self, tmp_path):
        from denai.tools.specs_analyzer import specs_analyze

        project_dir = tmp_path / "myproject"
        _make_specs_dir(tmp_path)
        ctx = {"path": str(project_dir), "project_name": "myproject"}

        with patch("denai.tools.specs_analyzer.get_context", return_value=ctx):
            result = await specs_analyze({"slug": "../../etc/passwd", "conversation_id": "abc"})

        assert "❌" in result
        assert "não encontrada" in result.lower()

    def test_tool_registered(self):
        from denai.tools.specs_analyzer import TOOLS

        assert len(TOOLS) == 1
        spec, func_name = TOOLS[0]
        assert spec["function"]["name"] == "specs_analyze"
        assert func_name == "specs_analyze"
