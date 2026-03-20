"""Testes do marketplace de plugins."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import create_app
from denai.marketplace import (
    BUNDLED_REGISTRY,
    _is_installed,
    get_registry,
    install_plugin,
    uninstall_plugin,
)
from denai.security.auth import API_KEY


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": API_KEY},
    ) as c:
        yield c


@pytest.fixture
def clean_plugins(tmp_path):
    """Use temp dir for plugins during tests."""
    with patch("denai.marketplace.PLUGINS_DIR", tmp_path):
        yield tmp_path


# ── Registry ─────────────────────────────────────────────────────


def test_bundled_registry_not_empty():
    assert len(BUNDLED_REGISTRY) >= 3


def test_bundled_registry_has_required_fields():
    for p in BUNDLED_REGISTRY:
        assert "id" in p
        assert "name" in p
        assert "description" in p
        assert "version" in p


def test_get_registry_marks_installed(clean_plugins):
    # Install a plugin manually
    (clean_plugins / "weather.py").write_text("# test")
    registry = get_registry()
    weather = next((p for p in registry if p["id"] == "weather"), None)
    assert weather is not None
    assert weather["installed"] is True


def test_get_registry_marks_not_installed(clean_plugins):
    registry = get_registry()
    weather = next((p for p in registry if p["id"] == "weather"), None)
    assert weather is not None
    assert weather["installed"] is False


# ── Install ──────────────────────────────────────────────────────


def test_install_bundled_plugin(clean_plugins):
    result = install_plugin("weather")
    assert result["ok"] is True
    assert (clean_plugins / "weather.py").exists()


def test_install_already_installed(clean_plugins):
    (clean_plugins / "weather.py").write_text("# existing")
    result = install_plugin("weather")
    assert "error" in result
    assert "já está instalado" in result["error"]


def test_install_unknown_plugin(clean_plugins):
    result = install_plugin("nonexistent")
    assert "error" in result
    assert "não encontrado" in result["error"]


# ── Uninstall ────────────────────────────────────────────────────


def test_uninstall_plugin(clean_plugins):
    (clean_plugins / "translator.py").write_text("# test")
    result = uninstall_plugin("translator")
    assert result["ok"] is True
    assert not (clean_plugins / "translator.py").exists()


def test_uninstall_dir_plugin(clean_plugins):
    plugin_dir = clean_plugins / "myplugin"
    plugin_dir.mkdir()
    (plugin_dir / "main.py").write_text("# test")
    result = uninstall_plugin("myplugin")
    assert result["ok"] is True
    assert not plugin_dir.exists()


def test_uninstall_not_installed(clean_plugins):
    result = uninstall_plugin("nonexistent")
    assert "error" in result


# ── API Endpoints ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_list_marketplace(client):
    resp = await client.get("/api/marketplace")
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    assert len(data["plugins"]) >= 3


@pytest.mark.asyncio
async def test_api_install_plugin(client, clean_plugins):
    resp = await client.post(
        "/api/marketplace/install",
        json={"plugin_id": "weather"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True


@pytest.mark.asyncio
async def test_api_install_missing_id(client):
    resp = await client.post(
        "/api/marketplace/install",
        json={},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_api_uninstall_plugin(client, clean_plugins):
    # First install
    (clean_plugins / "weather.py").write_text("# test")
    resp = await client.post(
        "/api/marketplace/uninstall",
        json={"plugin_id": "weather"},
    )
    assert resp.status_code == 200


# ── Is installed check ───────────────────────────────────────────


def test_is_installed_file(clean_plugins):
    assert _is_installed("foo") is False
    (clean_plugins / "foo.py").write_text("# test")
    assert _is_installed("foo") is True


def test_is_installed_dir(clean_plugins):
    assert _is_installed("bar") is False
    (clean_plugins / "bar").mkdir()
    assert _is_installed("bar") is True
