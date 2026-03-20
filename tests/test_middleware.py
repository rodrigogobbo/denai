"""Testes para o AuthMiddleware ASGI.

Verifica auth, rate limiting e que streaming SSE não é bufferizado.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL
from denai.version import VERSION


@pytest.fixture
async def app_instance(tmp_path):
    """Cria app com DB temporário."""
    db_path = tmp_path / "test_mw.db"

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
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()
        yield create_app()


# ── Auth Tests ──


@pytest.mark.asyncio
async def test_rejects_missing_api_key(app_instance):
    """Requisição sem API key deve retornar 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        resp = await client.get("/api/conversations")
        assert resp.status_code == 401
        assert "inválida" in resp.json()["error"]


@pytest.mark.asyncio
async def test_rejects_wrong_api_key(app_instance):
    """API key incorreta deve retornar 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
        headers={"X-API-Key": "wrong-key-12345"},
    ) as client:
        resp = await client.get("/api/conversations")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_accepts_valid_api_key_header(app_instance):
    """API key válida via header deve passar."""
    from denai.security.auth import API_KEY

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
        headers={"X-API-Key": API_KEY},
    ) as client:
        resp = await client.get("/api/conversations")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_accepts_valid_api_key_query_param(app_instance):
    """API key válida via query param deve passar."""
    from denai.security.auth import API_KEY

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        resp = await client.get(f"/api/conversations?key={API_KEY}")
        assert resp.status_code == 200


# ── Public Paths ──


@pytest.mark.asyncio
async def test_health_is_public(app_instance):
    """Endpoint /api/health deve funcionar sem API key."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
    ) as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == VERSION


# ── Rate Limiting ──


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess_requests(app_instance):
    """Deve bloquear após exceder limite de requisições."""
    from denai.security.auth import API_KEY
    from denai.security.rate_limit import rate_limiter

    rate_limiter.reset()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
        headers={"X-API-Key": API_KEY},
    ) as client:
        # Fazer 60 requisições legítimas para saturar
        for _ in range(60):
            await client.get("/api/conversations")

        # Próxima deve ser bloqueada
        resp = await client.get("/api/conversations")
        assert resp.status_code == 429
        assert "Rate limit" in resp.json()["error"]

    rate_limiter.reset()


# ── Streaming (SSE não bufferizado) ──


@pytest.mark.asyncio
async def test_streaming_response_not_buffered(app_instance):
    """Verifica que SSE chunks chegam incrementalmente (não bufferizados pelo middleware)."""
    from denai.security.auth import API_KEY

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_instance),
        base_url="http://testserver",
        headers={"X-API-Key": API_KEY},
    ) as client:
        # Criar uma conversa
        resp = await client.post("/api/conversations", json={"model": "test"})
        assert resp.status_code == 200
        conv_id = resp.json()["id"]

        # Mockar stream_chat para enviar chunks controlados
        async def fake_stream(messages, model, use_tools=True):
            import json

            yield f"data: {json.dumps({'content': 'Hello'})}\n\n"
            yield f"data: {json.dumps({'content': ' World'})}\n\n"
            yield 'data: {"done": true}\n\n'

        with patch("denai.routes.chat.stream_chat", fake_stream):
            resp = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "test", "model": "test"},
            )
            assert resp.status_code == 200
            assert resp.headers.get("content-type", "").startswith("text/event-stream")

            # Verificar que recebemos todos os chunks
            text = resp.text
            assert '"conversation_id"' in text
            assert '"content": "Hello"' in text
            assert '"content": " World"' in text
            assert '"done": true' in text
