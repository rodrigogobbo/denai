"""Tests for project persistence and prompt context injection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from denai.app import app
from denai.project import (
    ProjectInfo,
    _project_hash,
    context_to_prompt,
    is_context_stale,
    load_context,
    save_context,
)
from denai.security.auth import API_KEY

# ─── Persistence unit tests ─────────────────────────────────────────────


class TestProjectHash:
    """Test project path hashing."""

    def test_consistent_hash(self):
        h1 = _project_hash("/tmp/myproject")
        h2 = _project_hash("/tmp/myproject")
        assert h1 == h2

    def test_different_paths(self):
        h1 = _project_hash("/tmp/project-a")
        h2 = _project_hash("/tmp/project-b")
        assert h1 != h2

    def test_hash_length(self):
        h = _project_hash("/any/path")
        assert len(h) == 12

    def test_hash_is_hex(self):
        h = _project_hash("/any/path")
        int(h, 16)  # Should not raise


class TestSaveContext:
    """Test saving project context."""

    def test_save_creates_file(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(
                path="/tmp/test",
                name="test-proj",
                languages=["Python"],
                ecosystems=["PyPI"],
                frameworks=["FastAPI"],
            )
            ctx_file = save_context(info)
            assert ctx_file.is_file()

    def test_save_content(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(
                path="/tmp/test",
                name="test-proj",
                languages=["Python", "Go"],
                ecosystems=["PyPI"],
                frameworks=["FastAPI"],
                git_info={"branch": "main", "remote": "https://github.com/test/repo"},
                file_count=42,
                dir_count=5,
                description="A test project",
                key_files=["README.md"],
            )
            ctx_file = save_context(info)
            data = yaml.safe_load(ctx_file.read_text())

            assert data["project_name"] == "test-proj"
            assert data["languages"] == ["Python", "Go"]
            assert data["git_branch"] == "main"
            assert data["git_remote"] == "https://github.com/test/repo"
            assert data["file_count"] == 42
            assert data["analyzed_at"]

    def test_save_overwrites(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(path="/tmp/test", name="v1", languages=["Python"])
            save_context(info)

            info2 = ProjectInfo(path="/tmp/test", name="v2", languages=["Go"])
            ctx_file = save_context(info2)
            data = yaml.safe_load(ctx_file.read_text())
            assert data["project_name"] == "v2"
            assert data["languages"] == ["Go"]


class TestLoadContext:
    """Test loading project context."""

    def test_load_existing(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(path="/tmp/test", name="test-proj", languages=["Python"])
            save_context(info)
            loaded = load_context("/tmp/test")
            assert loaded is not None
            assert loaded["project_name"] == "test-proj"
            assert loaded["languages"] == ["Python"]

    def test_load_nonexistent(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            loaded = load_context("/tmp/does-not-exist")
            assert loaded is None

    def test_load_corrupted(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(path="/tmp/test", name="test")
            ctx_file = save_context(info)
            # Corrupt the file with non-dict YAML
            ctx_file.write_text("- just\n- a\n- list\n")
            loaded = load_context("/tmp/test")
            assert loaded is None

    def test_load_invalid_yaml(self, tmp_path):
        with patch("denai.project.PROJECTS_DIR", tmp_path / "projects"):
            info = ProjectInfo(path="/tmp/test", name="test")
            ctx_file = save_context(info)
            ctx_file.write_text(": : : invalid yaml {{{\n")
            loaded = load_context("/tmp/test")
            assert loaded is None


class TestIsContextStale:
    """Test staleness checking."""

    def test_fresh_context(self):
        ctx = {"analyzed_at": datetime.now(timezone.utc).isoformat()}
        assert is_context_stale(ctx) is False

    def test_old_context(self):
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        ctx = {"analyzed_at": old_date.isoformat()}
        assert is_context_stale(ctx) is True

    def test_custom_max_days(self):
        date_3d = datetime.now(timezone.utc) - timedelta(days=3)
        ctx = {"analyzed_at": date_3d.isoformat()}
        assert is_context_stale(ctx, max_days=2) is True
        assert is_context_stale(ctx, max_days=5) is False

    def test_missing_analyzed_at(self):
        assert is_context_stale({}) is True

    def test_invalid_date(self):
        assert is_context_stale({"analyzed_at": "not-a-date"}) is True

    def test_naive_datetime(self):
        """Test with naive datetime (no timezone info)."""
        ctx = {"analyzed_at": datetime.now().isoformat()}
        assert is_context_stale(ctx) is False


class TestContextToPrompt:
    """Test formatting context for system prompt."""

    def test_full_context(self):
        ctx = {
            "project_name": "myapp",
            "project_path": "/home/user/myapp",
            "languages": ["Python", "JavaScript"],
            "frameworks": ["FastAPI", "React"],
            "git_branch": "main",
            "git_remote": "https://github.com/user/myapp",
            "description": "A cool app",
            "file_count": 100,
            "dir_count": 15,
            "tree_depth_2": "myapp/\n├── src/\n└── tests/",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        prompt = context_to_prompt(ctx)
        assert "myapp" in prompt
        assert "Python" in prompt
        assert "FastAPI" in prompt
        assert "main" in prompt
        assert "100 arquivos" in prompt
        assert "```" in prompt

    def test_minimal_context(self):
        ctx = {
            "project_name": "minimal",
            "project_path": "/tmp/minimal",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        prompt = context_to_prompt(ctx)
        assert "minimal" in prompt
        assert "Linguagens" not in prompt

    def test_stale_context_warning(self):
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        ctx = {
            "project_name": "old",
            "project_path": "/tmp/old",
            "analyzed_at": old_date.isoformat(),
        }
        prompt = context_to_prompt(ctx)
        assert "⚠️" in prompt
        assert "/init" in prompt

    def test_no_tree(self):
        ctx = {
            "project_name": "test",
            "project_path": "/tmp/test",
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        prompt = context_to_prompt(ctx)
        assert "```" not in prompt


# ─── Prompt injection tests ─────────────────────────────────────────────


class TestPromptInjection:
    """Test that project context is injected into the system prompt."""

    def test_prompt_includes_context(self, tmp_path):
        ctx = {
            "project_name": "injected-project",
            "project_path": str(tmp_path),
            "languages": ["Python"],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        with patch("denai.project.load_context", return_value=ctx):
            from denai.llm.prompt import build_system_prompt

            prompt = build_system_prompt()
            assert "injected-project" in prompt
            assert "Contexto do Projeto" in prompt

    def test_prompt_without_context(self):
        with patch("denai.project.load_context", return_value=None):
            from denai.llm.prompt import build_system_prompt

            prompt = build_system_prompt()
            assert "DenAI" in prompt
            # No project block
            assert "Contexto do Projeto" not in prompt

    def test_prompt_handles_load_error(self):
        with patch("denai.project.load_context", side_effect=Exception("boom")):
            from denai.llm.prompt import build_system_prompt

            prompt = build_system_prompt()
            # Should not crash, just skip project block
            assert "DenAI" in prompt


# ─── API tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestProjectContextAPI:
    """Test the /api/project/context endpoint."""

    async def test_context_after_init(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            # Init first
            resp = await client.post("/api/project/init", json={"path": str(tmp_path)})
            assert resp.status_code == 200

            # Then get context
            resp = await client.get(f"/api/project/context?path={tmp_path}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["context"]["project_name"] == tmp_path.name

    async def test_context_not_found(self, tmp_path):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            resp = await client.get(f"/api/project/context?path={tmp_path / 'nonexistent'}")
            assert resp.status_code == 404
            data = resp.json()
            assert "error" in data

    async def test_init_saves_context(self, tmp_path):
        (tmp_path / "go.mod").write_text("module test")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            resp = await client.post("/api/project/init", json={"path": str(tmp_path)})
            assert resp.status_code == 200

            # Verify context was persisted
            ctx = load_context(str(tmp_path))
            assert ctx is not None
            assert "Go" in ctx["languages"]


# ─── Permissions — git default ───────────────────────────────────────────


class TestGitPermission:
    """Test that git has default 'ask' permission."""

    def test_git_default_is_ask(self):
        from denai.permissions import _DEFAULTS

        assert "git" in _DEFAULTS
        assert _DEFAULTS["git"] == "ask"
