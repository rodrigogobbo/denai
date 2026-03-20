"""Tests for project analysis (/init)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import app
from denai.project import ProjectInfo, _build_tree, analyze_project
from denai.security.auth import API_KEY

# ─── Unit tests ───


class TestProjectInfo:
    """Test ProjectInfo dataclass."""

    def test_empty_info(self):
        info = ProjectInfo()
        assert info.name == ""
        assert info.languages == []
        ctx = info.to_context()
        assert "Projeto:" in ctx

    def test_to_context_full(self):
        info = ProjectInfo(
            path="/tmp/test",
            name="test-project",
            languages=["Python", "JavaScript"],
            ecosystems=["PyPI", "Node.js"],
            frameworks=["FastAPI", "Docker"],
            key_files=["README.md", "Dockerfile"],
            file_count=42,
            dir_count=8,
            description="A test project",
            git_info={"branch": "main", "remote": "https://github.com/test/repo"},
        )
        ctx = info.to_context()
        assert "test-project" in ctx
        assert "Python" in ctx
        assert "JavaScript" in ctx
        assert "FastAPI" in ctx
        assert "main" in ctx
        assert "42 arquivos" in ctx
        assert "README.md" in ctx
        assert "A test project" in ctx

    def test_to_context_minimal(self):
        info = ProjectInfo(name="minimal", path="/tmp/minimal")
        ctx = info.to_context()
        assert "minimal" in ctx
        assert "Linguagens" not in ctx  # no languages detected

    def test_to_context_with_tree(self):
        info = ProjectInfo(name="proj", path="/p", tree="proj/\n├── src/\n└── README.md")
        ctx = info.to_context()
        assert "```" in ctx
        assert "src/" in ctx


class TestAnalyzeProject:
    """Test project analysis."""

    def test_analyze_nonexistent(self, tmp_path: Path):
        info = analyze_project(tmp_path / "nope")
        assert info.name == "nope"
        assert info.languages == []

    def test_analyze_empty_dir(self, tmp_path: Path):
        info = analyze_project(tmp_path)
        assert info.name == tmp_path.name
        assert info.file_count == 0
        assert info.languages == []

    def test_detect_python(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        info = analyze_project(tmp_path)
        assert "Python" in info.languages
        assert "PyPI" in info.ecosystems

    def test_detect_javascript(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        info = analyze_project(tmp_path)
        assert "JavaScript/TypeScript" in info.languages
        assert "Node.js" in info.ecosystems

    def test_detect_go(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/test")
        info = analyze_project(tmp_path)
        assert "Go" in info.languages

    def test_detect_rust(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        info = analyze_project(tmp_path)
        assert "Rust" in info.languages

    def test_detect_multiple_languages(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "package.json").write_text("{}")
        info = analyze_project(tmp_path)
        assert len(info.languages) >= 2

    def test_key_files(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Test\nA cool project")
        (tmp_path / "Dockerfile").write_text("FROM python:3")
        (tmp_path / ".gitignore").write_text("*.pyc")
        info = analyze_project(tmp_path)
        assert "README.md" in info.key_files
        assert "Dockerfile" in info.key_files

    def test_readme_description(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# My Project\nThis is a great tool for testing.")
        info = analyze_project(tmp_path)
        assert "great tool" in info.description

    def test_git_info(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/develop\n")
        (git_dir / "config").write_text('[remote "origin"]\n\turl = https://github.com/user/repo\n')
        info = analyze_project(tmp_path)
        assert info.git_info.get("branch") == "develop"
        assert "github.com" in info.git_info.get("remote", "")

    def test_tree_output(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "README.md").write_text("")
        info = analyze_project(tmp_path)
        assert info.tree
        assert "src/" in info.tree
        assert "tests/" in info.tree

    def test_ignores_node_modules(self, tmp_path: Path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "express").mkdir()
        (nm / "express" / "index.js").write_text("")
        (tmp_path / "index.js").write_text("")
        info = analyze_project(tmp_path)
        # Check that no tree line references node_modules/ as a directory entry
        tree_lines = info.tree.split("\n")
        assert not any("node_modules/" in line for line in tree_lines)
        # file_count should not include node_modules contents
        assert info.file_count == 1

    def test_file_and_dir_count(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.txt").write_text("c")
        info = analyze_project(tmp_path)
        assert info.file_count == 3
        assert info.dir_count == 1

    def test_detect_docker_framework(self, tmp_path: Path):
        (tmp_path / "Dockerfile").write_text("FROM node:18")
        info = analyze_project(tmp_path)
        assert "Docker" in info.frameworks

    def test_cwd_fallback(self, tmp_path: Path):
        """When no path given, uses cwd."""
        with patch("denai.project.Path.cwd", return_value=tmp_path):
            (tmp_path / "go.mod").write_text("module test")
            info = analyze_project(None)
            assert "Go" in info.languages


class TestBuildTree:
    """Test tree building."""

    def test_empty_dir(self, tmp_path: Path):
        tree = _build_tree(tmp_path)
        assert tmp_path.name in tree

    def test_max_depth(self, tmp_path: Path):
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "file.txt").write_text("")
        tree = _build_tree(tmp_path, max_depth=1)
        assert "a/" in tree
        assert "file.txt" not in tree  # too deep

    def test_sorts_dirs_first(self, tmp_path: Path):
        (tmp_path / "zebra.txt").write_text("")
        (tmp_path / "alpha").mkdir()
        tree = _build_tree(tmp_path)
        lines = tree.split("\n")
        # dir should come before file
        dir_idx = next(i for i, line in enumerate(lines) if "alpha/" in line)
        file_idx = next(i for i, line in enumerate(lines) if "zebra.txt" in line)
        assert dir_idx < file_idx


# ─── API tests ───


@pytest.mark.asyncio
class TestProjectAPI:
    """Test project API endpoints."""

    @pytest.fixture(autouse=True)
    def _mount_router(self):
        """Ensure the project router is mounted for API tests."""
        from denai.routes.project import router as project_router

        # Add router if not already included
        if project_router not in [r for r in app.router.routes]:
            app.include_router(project_router)
        yield

    async def test_post_init(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "README.md").write_text("# Test")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            resp = await client.post("/api/project/init", json={"path": str(tmp_path)})
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            assert data["project"]["name"] == tmp_path.name
            assert "Python" in data["project"]["languages"]
            assert data["context"]

    async def test_get_init(self, tmp_path: Path):
        (tmp_path / "package.json").write_text("{}")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            resp = await client.get(f"/api/project/init?path={tmp_path}")
            assert resp.status_code == 200
            data = resp.json()
            assert "JavaScript/TypeScript" in data["project"]["languages"]

    async def test_init_no_path(self):
        """Without path, uses cwd."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": API_KEY},
        ) as client:
            resp = await client.post("/api/project/init", json={})
            assert resp.status_code == 200
            data = resp.json()
            assert data["ok"] is True
            # Should analyze cwd (which is /tmp/denai itself)
            assert data["project"]["name"]
