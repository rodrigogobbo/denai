"""Testes para rotas de auto-atualização (/api/update)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL
from denai.routes.update import _parse_version

# ── Fixtures ──


@pytest.fixture
async def client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_update.db"

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


# ── _parse_version tests ──


class TestParseVersion:
    def test_simple(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_two_parts(self):
        assert _parse_version("0.6") == (0, 6)

    def test_four_parts_truncated(self):
        assert _parse_version("1.2.3.4") == (1, 2, 3)

    def test_with_non_numeric(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_comparison_greater(self):
        assert _parse_version("0.7.0") > _parse_version("0.6.0")

    def test_comparison_equal(self):
        assert _parse_version("0.6.0") == _parse_version("0.6.0")

    def test_comparison_less(self):
        assert _parse_version("0.5.9") < _parse_version("0.6.0")

    def test_comparison_minor(self):
        assert _parse_version("0.6.1") > _parse_version("0.6.0")

    def test_comparison_major(self):
        assert _parse_version("1.0.0") > _parse_version("0.99.99")


# ── GET /api/update/check ──


@pytest.mark.asyncio
async def test_check_update_returns_current_version(client):
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "0.6.0"}}
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    assert resp.status_code == 200
    data = resp.json()
    assert "current_version" in data
    from denai.version import VERSION

    assert data["current_version"] == VERSION


@pytest.mark.asyncio
async def test_check_update_available(client):
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        pypi_resp = MagicMock()
        pypi_resp.status_code = 200
        pypi_resp.json.return_value = {"info": {"version": "1.0.0"}}
        github_resp = MagicMock()
        github_resp.status_code = 404  # sem release notes no GitHub
        mock_client.get.side_effect = [pypi_resp, github_resp]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        with patch("denai.routes.update._extract_changelog", return_value=None):
            resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is True
    assert data["latest_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_check_update_includes_release_notes(client):
    """Quando há atualização, inclui notas de release do GitHub."""
    notes = "## [1.0.0]\n\n### Adicionado\n- Feature X\n- Feature Y"
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        pypi_resp = MagicMock()
        pypi_resp.status_code = 200
        pypi_resp.json.return_value = {"info": {"version": "1.0.0"}}
        github_resp = MagicMock()
        github_resp.status_code = 200
        github_resp.json.return_value = {"body": notes}
        mock_client.get.side_effect = [pypi_resp, github_resp]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is True
    assert "release_notes" in data
    assert "Feature X" in data["release_notes"]


@pytest.mark.asyncio
async def test_check_update_fallback_to_changelog(client):
    """Sem release no GitHub, faz fallback para CHANGELOG.md local."""
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        pypi_resp = MagicMock()
        pypi_resp.status_code = 200
        pypi_resp.json.return_value = {"info": {"version": "1.0.0"}}
        github_resp = MagicMock()
        github_resp.status_code = 404
        mock_client.get.side_effect = [pypi_resp, github_resp]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        with patch("denai.routes.update._extract_changelog", return_value="## [1.0.0]\n- changelog local"):
            resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is True
    assert data.get("release_notes") == "## [1.0.0]\n- changelog local"


@pytest.mark.asyncio
async def test_check_update_not_available(client):
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "0.6.0"}}
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is False


@pytest.mark.asyncio
async def test_check_update_pypi_error(client):
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is False
    assert "error" in data


@pytest.mark.asyncio
async def test_check_update_network_error(client):
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("no internet")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is False
    assert "error" in data


# ── POST /api/update/install (SSE streaming) ──


def _make_mock_proc(lines: list[bytes], returncode: int = 0):
    """Helper: cria mock de subprocess para o streaming SSE."""
    line_iter = iter(lines + [b""])

    mock_proc = AsyncMock()
    mock_proc.returncode = returncode
    mock_proc.stdout = AsyncMock()
    mock_proc.stdout.readline = AsyncMock(side_effect=lambda: next(line_iter))
    mock_proc.wait = AsyncMock(return_value=returncode)
    return mock_proc


async def _collect_sse(resp) -> list[dict]:
    """Coleta e parseia todos os eventos SSE de uma resposta."""
    import json

    events = []
    content = resp.content.decode()
    for line in content.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


@pytest.mark.asyncio
async def test_install_streams_progress_lines(client):
    """Linhas do pip aparecem como eventos 'progress'."""
    mock_proc = _make_mock_proc(
        [
            b"Collecting denai\n",
            b"Downloading denai-1.0.0.tar.gz\n",
            b"Successfully installed denai-1.0.0\n",
        ]
    )

    # Mock _get_installed_version diretamente
    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        patch("denai.routes.update._get_installed_version", return_value="1.0.0"),
    ):
        resp = await client.post("/api/update/install")

    assert resp.status_code == 200
    events = await _collect_sse(resp)

    progress_events = [e for e in events if e.get("type") == "progress"]
    assert len(progress_events) >= 1

    success_events = [e for e in events if e.get("type") == "success"]
    assert len(success_events) == 1
    assert "1.0.0" in success_events[0].get("version", "")


@pytest.mark.asyncio
async def test_install_streams_error_on_failure(client):
    """Código de saída != 0 gera evento 'error'."""
    mock_proc = _make_mock_proc([b"ERROR: Could not find a version\n"], returncode=1)

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        resp = await client.post("/api/update/install")

    events = await _collect_sse(resp)
    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) >= 1


@pytest.mark.asyncio
async def test_install_response_is_streaming(client):
    """Resposta deve ser text/event-stream."""
    mock_proc = _make_mock_proc([b"Installing\n"])

    with (
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        patch("denai.routes.update._get_installed_version", return_value="0.18.0"),
    ):
        resp = await client.post("/api/update/install")

    assert "text/event-stream" in resp.headers.get("content-type", "")


# ── POST /api/update/restart ──


@pytest.mark.asyncio
async def test_restart_returns_ok(client):
    """Endpoint de restart retorna ok=True."""
    import denai.routes.update as update_mod

    update_mod._restart_scheduled = False  # reset flag

    with patch("asyncio.create_task"):  # não executar o restart real
        resp = await client.post("/api/update/restart")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "reconnect_delay_ms" in data

    update_mod._restart_scheduled = False  # limpar após teste


@pytest.mark.asyncio
async def test_restart_not_duplicate(client):
    """Segunda chamada enquanto restart pendente retorna erro."""
    import denai.routes.update as update_mod

    update_mod._restart_scheduled = True

    resp = await client.post("/api/update/restart")
    data = resp.json()
    assert data["ok"] is False

    update_mod._restart_scheduled = False


@pytest.mark.asyncio
async def test_get_installed_version():
    """_get_installed_version parseia saída do pip show."""
    from denai.routes.update import _get_installed_version

    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (
        b"Name: denai\nVersion: 0.18.0\nSummary: Your private AI\n",
        b"",
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        version = await _get_installed_version()

    assert version == "0.18.0"
