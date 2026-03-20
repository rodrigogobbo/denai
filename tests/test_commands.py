"""Testes de custom commands."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.commands import (
    Command,
    _parse_command_file,
    _split_arguments,
    discover_commands,
    get_command,
    render_command,
)
from denai.db import SCHEMA_SQL


@pytest.fixture
async def client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_commands.db"
    plans_db_path = tmp_path / "plans.db"

    import aiosqlite

    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.config.DATA_DIR", tmp_path),
        patch("denai.tools.planning.PLANS_DB", plans_db_path),
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


@pytest.fixture
def commands_dir(tmp_path):
    with patch("denai.commands.COMMANDS_DIR", tmp_path):
        yield tmp_path


# ── Parsing ──────────────────────────────────────────────────────


def test_parse_simple_command(commands_dir):
    f = commands_dir / "test.md"
    f.write_text("Rode os testes do projeto.")
    cmd = _parse_command_file(f)
    assert cmd is not None
    assert cmd.name == "test"
    assert cmd.template == "Rode os testes do projeto."


def test_parse_command_with_frontmatter(commands_dir):
    f = commands_dir / "review.md"
    f.write_text("---\ndescription: Review code\nmodel: llama3.2:3b\n---\nReview the code.")
    cmd = _parse_command_file(f)
    assert cmd is not None
    assert cmd.description == "Review code"
    assert cmd.model == "llama3.2:3b"
    assert cmd.template == "Review the code."


def test_parse_empty_file(commands_dir):
    f = commands_dir / "empty.md"
    f.write_text("")
    assert _parse_command_file(f) is None


def test_parse_frontmatter_only(commands_dir):
    f = commands_dir / "meta.md"
    f.write_text("---\ndescription: No template\n---\n")
    assert _parse_command_file(f) is None


# ── Discovery ────────────────────────────────────────────────────


def test_discover_commands(commands_dir):
    (commands_dir / "a.md").write_text("Template A")
    (commands_dir / "b.md").write_text("Template B")
    (commands_dir / "not-md.txt").write_text("Ignored")
    cmds = discover_commands()
    assert len(cmds) == 2
    names = [c.name for c in cmds]
    assert "a" in names
    assert "b" in names


def test_discover_empty_dir(commands_dir):
    assert discover_commands() == []


def test_get_command(commands_dir):
    (commands_dir / "deploy.md").write_text("---\ndescription: Deploy\n---\nDeploy to production")
    cmd = get_command("deploy")
    assert cmd is not None
    assert cmd.name == "deploy"


def test_get_command_not_found(commands_dir):
    assert get_command("nonexistent") is None


# ── Rendering ────────────────────────────────────────────────────


def test_render_with_arguments():
    cmd = Command(name="explain", template="Explique $ARGUMENTS para mim")
    result = render_command(cmd, "decorators em Python")
    assert result == "Explique decorators em Python para mim"


def test_render_positional_args():
    cmd = Command(name="create", template="Crie arquivo $1 no diretório $2")
    result = render_command(cmd, "config.json src")
    assert result == "Crie arquivo config.json no diretório src"


def test_render_quoted_args():
    cmd = Command(name="t", template="$1 | $2")
    result = render_command(cmd, 'hello "world is big"')
    assert result == "hello | world is big"


def test_render_no_args():
    cmd = Command(name="test", template="Rode os testes")
    result = render_command(cmd, "")
    assert result == "Rode os testes"


def test_render_cleans_unreplaced():
    cmd = Command(name="t", template="Do $1 and $2 and $3")
    result = render_command(cmd, "first")
    assert result == "Do first and  and"


# ── Argument splitting ───────────────────────────────────────────


def test_split_simple():
    assert _split_arguments("a b c") == ["a", "b", "c"]


def test_split_quoted():
    assert _split_arguments('a "b c" d') == ["a", "b c", "d"]


def test_split_single_quoted():
    assert _split_arguments("a 'b c' d") == ["a", "b c", "d"]


def test_split_empty():
    assert _split_arguments("") == []
    assert _split_arguments("   ") == []


# ── API Endpoints ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_list_commands(client, commands_dir):
    (commands_dir / "test.md").write_text("---\ndescription: Run tests\n---\nRun all tests")
    resp = await client.get("/api/commands")
    assert resp.status_code == 200
    data = resp.json()
    assert "commands" in data
    assert any(c["name"] == "test" for c in data["commands"])


@pytest.mark.asyncio
async def test_api_list_commands_empty(client, commands_dir):
    resp = await client.get("/api/commands")
    assert resp.status_code == 200
    assert resp.json()["commands"] == []


@pytest.mark.asyncio
async def test_api_run_command(client, commands_dir):
    (commands_dir / "greet.md").write_text("Hello $ARGUMENTS!")
    resp = await client.post(
        "/api/commands/run",
        json={"name": "greet", "arguments": "World"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["prompt"] == "Hello World!"


@pytest.mark.asyncio
async def test_api_run_command_not_found(client, commands_dir):
    resp = await client.post(
        "/api/commands/run",
        json={"name": "nonexistent"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_api_run_missing_name(client):
    resp = await client.post("/api/commands/run", json={})
    assert resp.status_code == 200
    assert "error" in resp.json()
