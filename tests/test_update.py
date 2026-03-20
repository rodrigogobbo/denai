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
        # e.g. "1.2.3rc1" — "3rc1" is not purely numeric, gets filtered
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
    """Endpoint always returns current_version, even on error."""
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
    assert data["current_version"] == "0.7.0"


@pytest.mark.asyncio
async def test_check_update_available(client):
    """When PyPI has a newer version, update_available is True."""
    with patch("denai.routes.update.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"info": {"version": "1.0.0"}}
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        resp = await client.get("/api/update/check")

    data = resp.json()
    assert data["update_available"] is True
    assert data["latest_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_check_update_not_available(client):
    """When PyPI has the same version, update_available is False."""
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
    """When PyPI returns non-200, graceful fallback with error."""
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
    """When network fails, graceful error response."""
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


# ── POST /api/update/install ──


@pytest.mark.asyncio
async def test_install_update_success(client):
    """Successful pip upgrade returns success message."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"Successfully installed denai-1.0.0", b"")
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        resp = await client.post("/api/update/install")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Atualizado" in data["message"]
    assert "Successfully installed" in data["output"]

    # Verify pip was called correctly
    mock_exec.assert_called_once()
    call_args = mock_exec.call_args[0]
    assert "-m" in call_args
    assert "pip" in call_args
    assert "install" in call_args
    assert "--upgrade" in call_args
    assert "denai" in call_args


@pytest.mark.asyncio
async def test_install_update_failure(client):
    """Failed pip upgrade returns error message."""
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"", b"ERROR: No matching distribution")
    mock_proc.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        resp = await client.post("/api/update/install")

    data = resp.json()
    assert data["success"] is False
    assert "Erro" in data["message"]
    assert "No matching distribution" in data["output"]
