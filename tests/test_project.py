"""Tests for project analysis (/init)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import app
from denai.project import (
    ProjectInfo,
    _build_tree,
    _count_entries,
    _detect_frameworks,
    _detect_key_files,
    _detect_languages,
    _read_description,
    _read_git_info,
    analyze_project,
)
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
        return

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


# ─── Extracted helpers ───


class TestDetectLanguages:
    """Test the _detect_languages helper."""

    def test_python_detected(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        langs, ecos = _detect_languages(tmp_path)
        assert "Python" in langs
        assert "PyPI" in ecos

    def test_multiple_languages(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module test")
        (tmp_path / "package.json").write_text("{}")
        langs, ecos = _detect_languages(tmp_path)
        assert "Go" in langs
        assert "JavaScript/TypeScript" in langs

    def test_glob_patterns(self, tmp_path: Path):
        (tmp_path / "app.csproj").write_text("<Project/>")
        langs, _ = _detect_languages(tmp_path)
        assert "C#" in langs

    def test_empty_dir(self, tmp_path: Path):
        langs, ecos = _detect_languages(tmp_path)
        assert langs == set()
        assert ecos == set()


class TestDetectFrameworks:
    """Test the _detect_frameworks helper."""

    def test_dockerfile(self, tmp_path: Path):
        (tmp_path / "Dockerfile").write_text("FROM python:3")
        frameworks = _detect_frameworks(tmp_path)
        assert "Docker" in frameworks

    def test_nested_hint(self, tmp_path: Path):
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("on: push")
        frameworks = _detect_frameworks(tmp_path)
        assert "GitHub Actions CI" in frameworks

    def test_child_dir_hint(self, tmp_path: Path):
        sub = tmp_path / "backend"
        sub.mkdir()
        (sub / "Dockerfile").write_text("FROM node:18")
        frameworks = _detect_frameworks(tmp_path)
        assert "Docker" in frameworks

    def test_empty_dir(self, tmp_path: Path):
        frameworks = _detect_frameworks(tmp_path)
        assert frameworks == set()


class TestDetectKeyFiles:
    """Test the _detect_key_files helper."""

    def test_finds_readme_and_license(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Hi")
        (tmp_path / "LICENSE").write_text("MIT")
        (tmp_path / "random.txt").write_text("noise")
        key = _detect_key_files(tmp_path)
        assert "README.md" in key
        assert "LICENSE" in key
        assert "random.txt" not in key

    def test_returns_sorted(self, tmp_path: Path):
        (tmp_path / "Makefile").write_text("")
        (tmp_path / "Dockerfile").write_text("")
        (tmp_path / ".gitignore").write_text("")
        key = _detect_key_files(tmp_path)
        assert key == sorted(key)

    def test_empty_dir(self, tmp_path: Path):
        assert _detect_key_files(tmp_path) == []


class TestReadDescription:
    """Test the _read_description helper."""

    def test_reads_first_content_line(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Title\nThis is the description.\n")
        desc = _read_description(tmp_path)
        assert desc == "This is the description."

    def test_skips_headings(self, tmp_path: Path):
        (tmp_path / "README.md").write_text("# H1\n## H2\nActual text here.\n")
        desc = _read_description(tmp_path)
        assert desc == "Actual text here."

    def test_truncates_long_lines(self, tmp_path: Path):
        long_line = "A" * 300
        (tmp_path / "README.md").write_text(f"# Title\n{long_line}\n")
        desc = _read_description(tmp_path)
        assert len(desc) == 200

    def test_no_readme(self, tmp_path: Path):
        assert _read_description(tmp_path) == ""

    def test_rst_readme(self, tmp_path: Path):
        # RST headings use underlines, so "Title" is just plain text to our parser
        (tmp_path / "README.rst").write_text("=====\nRST description.\n")
        desc = _read_description(tmp_path)
        assert desc == "RST description."


class TestReadGitInfo:
    """Test the _read_git_info helper."""

    def test_branch_and_remote(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/feature\n")
        (git_dir / "config").write_text('[remote "origin"]\n\turl = git@github.com:user/repo\n')
        info = _read_git_info(tmp_path)
        assert info["branch"] == "feature"
        assert "github.com" in info["remote"]

    def test_no_git_dir(self, tmp_path: Path):
        assert _read_git_info(tmp_path) == {}

    def test_detached_head(self, tmp_path: Path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("abc123def456\n")
        info = _read_git_info(tmp_path)
        assert "branch" not in info


class TestCountEntries:
    """Test the _count_entries helper."""

    def test_files_and_dirs(self, tmp_path: Path):
        (tmp_path / "a.txt").write_text("a")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("b")
        fc, dc = _count_entries(tmp_path)
        assert fc == 2
        assert dc == 1

    def test_ignores_hidden_and_noise(self, tmp_path: Path):
        (tmp_path / "real.py").write_text("")
        (tmp_path / ".hidden").write_text("")
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("")
        fc, dc = _count_entries(tmp_path)
        assert fc == 1
        assert dc == 0

    def test_empty_dir(self, tmp_path: Path):
        fc, dc = _count_entries(tmp_path)
        assert fc == 0
        assert dc == 0
