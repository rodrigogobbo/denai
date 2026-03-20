"""Testes do sistema de providers multi-model."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL
from denai.llm.providers import (
    Provider,
    _convert_messages_to_openai,
    _convert_tools_to_openai,
    _providers,
    get_all_providers,
    get_provider,
    register_provider,
)


@pytest.fixture
async def client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_providers.db"

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


@pytest.fixture(autouse=True)
def reset_providers():
    """Reset providers between tests."""
    _providers.clear()
    yield
    _providers.clear()


# ── Provider Registration ─────────────────────────────────────────


def test_register_provider():
    p = Provider(name="TestProvider", kind="openai", base_url="http://localhost:1234")
    register_provider(p)
    assert get_provider("testprovider") is p


def test_default_provider_is_ollama():
    from denai.llm.providers import get_default_provider

    p = get_default_provider()
    assert p.kind == "ollama"
    assert p.name == "Ollama"


def test_provider_properties():
    p1 = Provider(name="A", kind="ollama", base_url="http://x")
    assert p1.is_ollama
    assert not p1.is_openai_compatible
    assert not p1.is_gpt4all

    p2 = Provider(name="B", kind="openai", base_url="http://y")
    assert p2.is_openai_compatible
    assert not p2.is_ollama

    p3 = Provider(name="C", kind="gpt4all", base_url="")
    assert p3.is_gpt4all


def test_get_all_providers():
    register_provider(Provider(name="P1", kind="openai", base_url="http://a"))
    register_provider(Provider(name="P2", kind="openai", base_url="http://b"))
    providers = get_all_providers()
    names = {p.name for p in providers}
    assert "P1" in names
    assert "P2" in names
    assert "Ollama" in names  # default


# ── Message conversion ────────────────────────────────────────────


def test_convert_messages_to_openai():
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    result = _convert_messages_to_openai(messages)
    assert len(result) == 3
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "Hello"


def test_convert_messages_with_tool_calls():
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": "web_search", "arguments": {"query": "test"}}}],
        }
    ]
    result = _convert_messages_to_openai(messages)
    assert result[0]["tool_calls"][0]["type"] == "function"
    assert result[0]["tool_calls"][0]["function"]["name"] == "web_search"


def test_convert_tools_to_openai():
    tools = [
        {
            "function": {
                "name": "web_search",
                "description": "Search the web",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            }
        }
    ]
    result = _convert_tools_to_openai(tools)
    assert result[0]["type"] == "function"
    assert result[0]["function"]["name"] == "web_search"


# ── Load from config ─────────────────────────────────────────────


def test_load_providers_from_config():
    from denai.llm.providers import load_providers_from_config

    config = {
        "providers": [
            {"name": "LM Studio", "kind": "openai", "base_url": "http://localhost:1234"},
            {"name": "BadProvider"},  # missing base_url but has default
        ]
    }
    load_providers_from_config(config)
    p = get_provider("lm studio")
    assert p is not None
    assert p.kind == "openai"


# ── API Endpoints ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_providers(client):
    resp = await client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    # At least Ollama should be there
    names = [p["name"] for p in data["providers"]]
    assert "Ollama" in names


@pytest.mark.asyncio
async def test_add_provider(client):
    resp = await client.post(
        "/api/providers",
        json={
            "name": "LM Studio",
            "kind": "openai",
            "base_url": "http://localhost:1234",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_add_provider_missing_fields(client):
    resp = await client.post("/api/providers", json={"kind": "openai"})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
