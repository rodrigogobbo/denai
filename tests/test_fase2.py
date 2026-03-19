"""Testes para features da Fase 2 do DenAI.

Valida os endpoints de export (JSON/Markdown), busca de conversas
e status do Ollama.
"""

import uuid
from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL, get_db

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
async def app_with_client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_fase2.db"

    import aiosqlite

    # Init DB manually
    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    # Patch DB_PATH in both config and db modules
    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
    ):
        _app = create_app()

        from denai.security.auth import API_KEY
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as client:
            yield client


@pytest.fixture
async def client_with_conversation(app_with_client):
    """Client + conversa com 4 mensagens criada."""
    client = app_with_client

    # Criar conversa
    resp = await client.post("/api/conversations", json={"model": "llama3.1:8b"})
    assert resp.status_code == 200
    conv_id = resp.json()["id"]

    # Inserir mensagens e atualizar título
    async with get_db() as db:
        now = datetime.now().isoformat()
        messages = [
            (str(uuid.uuid4())[:12], conv_id, "user", "Qual a capital do Brasil?", now),
            (str(uuid.uuid4())[:12], conv_id, "assistant", "A capital do Brasil é Brasília.", now),
            (str(uuid.uuid4())[:12], conv_id, "user", "E a população?", now),
            (
                str(uuid.uuid4())[:12],
                conv_id,
                "assistant",
                "Brasília tem aproximadamente 3 milhões de habitantes.",
                now,
            ),
        ]
        await db.executemany(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            messages,
        )
        await db.execute("UPDATE conversations SET title = ? WHERE id = ?", ("Capital do Brasil", conv_id))
        await db.commit()

    return client, conv_id


@pytest.fixture
async def client_with_multiple_conversations(app_with_client):
    """Client + 3 conversas com mensagens."""
    client = app_with_client
    conv_ids = []
    titles = ["Deploy com Docker", "Debug de Python", "Configuração do Nginx"]

    for title in titles:
        resp = await client.post("/api/conversations", json={"model": "llama3.1:8b"})
        conv_id = resp.json()["id"]
        conv_ids.append(conv_id)

        async with get_db() as db:
            await db.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4())[:12],
                    conv_id,
                    "user",
                    f"Conversa sobre {title.lower()}",
                    datetime.now().isoformat(),
                ),
            )
            await db.commit()

    return client, conv_ids


# ── Export JSON ─────────────────────────────────────────────────────────


class TestExportJSON:
    """Testes para GET /api/conversations/{id}/export?format=json."""

    async def test_export_json_returns_200(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        assert resp.status_code == 200

    async def test_export_json_content_type(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        assert "application/json" in resp.headers.get("content-type", "")

    async def test_export_json_has_messages(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        data = resp.json()
        assert "messages" in data
        assert len(data["messages"]) == 4

    async def test_export_json_messages_have_role_and_content(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        for msg in resp.json()["messages"]:
            assert "role" in msg
            assert "content" in msg

    async def test_export_json_preserves_order(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        msgs = resp.json()["messages"]
        assert msgs[0]["role"] == "user"
        assert "capital" in msgs[0]["content"].lower()
        assert msgs[1]["role"] == "assistant"

    async def test_export_json_has_metadata(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=json")
        data = resp.json()
        assert "id" in data
        assert "title" in data

    async def test_export_json_not_found(self, app_with_client):
        resp = await app_with_client.get("/api/conversations/nonexistent/export?format=json")
        assert resp.status_code == 404


# ── Export Markdown ─────────────────────────────────────────────────────


class TestExportMarkdown:
    """Testes para GET /api/conversations/{id}/export?format=markdown."""

    async def test_export_markdown_returns_200(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=markdown")
        assert resp.status_code == 200

    async def test_export_markdown_content_type(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=markdown")
        assert "text/" in resp.headers.get("content-type", "")

    async def test_export_markdown_has_roles(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=markdown")
        text = resp.text
        assert "Usuário" in text or "User" in text
        assert "DenAI" in text or "Assistant" in text

    async def test_export_markdown_has_content(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=markdown")
        assert "Brasília" in resp.text

    async def test_export_markdown_has_title(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=markdown")
        assert "Capital do Brasil" in resp.text

    async def test_export_markdown_not_found(self, app_with_client):
        resp = await app_with_client.get("/api/conversations/nonexistent/export?format=markdown")
        assert resp.status_code == 404


# ── Search ──────────────────────────────────────────────────────────────


class TestSearch:
    """Testes para GET /api/conversations/search?q=term."""

    async def test_search_by_title(self, client_with_multiple_conversations):
        client, _ = client_with_multiple_conversations
        resp = await client.get("/api/conversations/search?q=Docker")
        assert resp.status_code == 200
        results = resp.json().get("results", [])
        assert len(results) >= 1
        assert any("Docker" in r.get("title", "") for r in results)

    async def test_search_by_message_content(self, client_with_multiple_conversations):
        client, _ = client_with_multiple_conversations
        resp = await client.get("/api/conversations/search?q=nginx")
        assert resp.status_code == 200
        results = resp.json().get("results", [])
        assert len(results) >= 1

    async def test_search_no_results(self, client_with_multiple_conversations):
        client, _ = client_with_multiple_conversations
        resp = await client.get("/api/conversations/search?q=xyznonexistent123")
        assert resp.status_code == 200
        assert len(resp.json().get("results", [])) == 0

    async def test_search_case_insensitive(self, client_with_multiple_conversations):
        client, _ = client_with_multiple_conversations
        r1 = await client.get("/api/conversations/search?q=docker")
        r2 = await client.get("/api/conversations/search?q=DOCKER")
        assert len(r1.json().get("results", [])) == len(r2.json().get("results", []))

    async def test_search_returns_metadata(self, client_with_multiple_conversations):
        client, _ = client_with_multiple_conversations
        resp = await client.get("/api/conversations/search?q=Python")
        results = resp.json().get("results", [])
        if results:
            assert "id" in results[0]
            assert "title" in results[0]


# ── Ollama Status ───────────────────────────────────────────────────────


class TestOllamaStatus:
    """Testes para GET /api/ollama/status."""

    async def test_always_returns_200(self, app_with_client):
        resp = await app_with_client.get("/api/ollama/status")
        assert resp.status_code == 200

    async def test_has_status_field(self, app_with_client):
        resp = await app_with_client.get("/api/ollama/status")
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("online", "offline")

    async def test_offline_when_unreachable(self, app_with_client):
        """Status deve ser 'offline' quando Ollama não está acessível."""
        with patch("denai.routes.models.OLLAMA_URL", "http://127.0.0.1:99999"):
            resp = await app_with_client.get("/api/ollama/status")
        data = resp.json()
        assert data["status"] == "offline"

    async def test_has_version_field(self, app_with_client):
        resp = await app_with_client.get("/api/ollama/status")
        data = resp.json()
        assert "version" in data

    async def test_has_models_count(self, app_with_client):
        resp = await app_with_client.get("/api/ollama/status")
        data = resp.json()
        assert "models_count" in data
        assert isinstance(data["models_count"], int)
