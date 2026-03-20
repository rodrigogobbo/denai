"""Tests for HTML export."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL, get_db
from denai.export_html import (
    _extract_tool_name,
    _fmt_date,
    _fmt_time,
    _render_content,
    _render_message,
    conversation_to_html,
)

# ── Unit Tests ─────────────────────────────────────────────────────────


class TestConversationToHtml:
    """Test full HTML generation."""

    def test_basic(self):
        conv = {
            "title": "Test Chat",
            "model": "llama3",
            "created_at": "2026-01-01T12:00:00",
        }
        messages = [
            {"role": "user", "content": "Hello", "created_at": "2026-01-01T12:00:00"},
            {
                "role": "assistant",
                "content": "Hi there!",
                "created_at": "2026-01-01T12:00:01",
            },
        ]
        result = conversation_to_html(conv, messages)
        assert "<!DOCTYPE html>" in result
        assert "Test Chat" in result
        assert "Hello" in result
        assert "Hi there!" in result
        assert "llama3" in result
        assert "DenAI" in result

    def test_escapes_html_in_title(self):
        conv = {
            "title": "<script>alert('xss')</script>",
            "model": "",
            "created_at": "",
        }
        result = conversation_to_html(conv, [])
        # The XSS payload should be escaped in the title, not rendered raw
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in result
        # The title tag should contain escaped version
        assert "<title>&lt;script&gt;" in result

    def test_empty_messages(self):
        conv = {"title": "Empty", "model": "", "created_at": ""}
        result = conversation_to_html(conv, [])
        assert "<!DOCTYPE html>" in result
        assert "0 mensagens" in result

    def test_tool_messages(self):
        conv = {"title": "Tools", "model": "", "created_at": ""}
        messages = [
            {
                "role": "tool",
                "content": '{"name": "file_read", "result": "ok"}',
                "created_at": "",
            },
        ]
        result = conversation_to_html(conv, messages)
        assert "🔧" in result

    def test_system_messages_excluded(self):
        conv = {"title": "Sys", "model": "", "created_at": ""}
        messages = [
            {"role": "system", "content": "System prompt", "created_at": ""},
            {"role": "user", "content": "Hello", "created_at": ""},
        ]
        result = conversation_to_html(conv, messages)
        # system messages should not appear
        assert "System prompt" not in result
        assert "Hello" in result

    def test_empty_content_skipped(self):
        conv = {"title": "Skip", "model": "", "created_at": ""}
        messages = [
            {"role": "user", "content": "", "created_at": ""},
            {"role": "user", "content": "Real message", "created_at": ""},
        ]
        result = conversation_to_html(conv, messages)
        assert "Real message" in result

    def test_responsive(self):
        result = conversation_to_html({"title": "Test", "model": "", "created_at": ""}, [])
        assert "@media" in result
        assert "max-width" in result


class TestRenderContent:
    """Test markdown-to-HTML conversion."""

    def test_plain_text(self):
        result = _render_content("Hello world")
        assert "Hello world" in result

    def test_bold(self):
        result = _render_content("**bold text**")
        assert "<strong>bold text</strong>" in result

    def test_italic(self):
        result = _render_content("*italic*")
        assert "<em>italic</em>" in result

    def test_code_inline(self):
        result = _render_content("use `pip install`")
        assert "<code>pip install</code>" in result

    def test_code_block(self):
        result = _render_content("```python\nprint('hi')\n```")
        assert "<pre>" in result
        assert "print" in result

    def test_headers(self):
        result = _render_content("# Title\n## Subtitle")
        assert "<h1>" in result
        assert "<h2>" in result

    def test_link(self):
        result = _render_content("[click](https://example.com)")
        assert 'href="https://example.com"' in result
        assert "click" in result

    def test_escapes_html(self):
        result = _render_content("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_empty(self):
        assert _render_content("") == ""

    def test_list(self):
        result = _render_content("- item 1\n- item 2")
        assert "<li>" in result

    def test_blockquote(self):
        result = _render_content("> quoted text")
        assert "<blockquote>" in result


class TestRenderMessage:
    """Test individual message rendering."""

    def test_user_message(self):
        msg = {
            "role": "user",
            "content": "Hello",
            "created_at": "2026-01-01T12:00:00",
        }
        result = _render_message(msg)
        assert "message user" in result
        assert "👤" in result
        assert "Hello" in result

    def test_assistant_message(self):
        msg = {
            "role": "assistant",
            "content": "Hi!",
            "created_at": "2026-01-01T12:00:00",
        }
        result = _render_message(msg)
        assert "message assistant" in result
        assert "🐺" in result

    def test_tool_message(self):
        msg = {"role": "tool", "content": "file contents here", "created_at": ""}
        result = _render_message(msg)
        assert "🔧" in result
        assert "tool-card" in result

    def test_system_ignored(self):
        msg = {"role": "system", "content": "system prompt", "created_at": ""}
        result = _render_message(msg)
        assert result == ""

    def test_empty_content(self):
        msg = {"role": "user", "content": "", "created_at": ""}
        # The parent filters empty, but render should still work
        result = _render_message(msg)
        assert "user" in result


class TestHelpers:
    """Test helper functions."""

    def test_fmt_time(self):
        assert _fmt_time("2026-01-15T14:30:00") == "14:30"

    def test_fmt_time_invalid(self):
        assert _fmt_time("invalid") == ""

    def test_fmt_time_empty(self):
        assert _fmt_time("") == ""

    def test_fmt_date(self):
        assert _fmt_date("2026-01-15T14:30:00") == "15/01/2026 14:30"

    def test_fmt_date_invalid(self):
        assert _fmt_date("nope") == ""

    def test_extract_tool_name_json(self):
        assert _extract_tool_name('{"name": "file_read"}') == "file_read"

    def test_extract_tool_name_fallback(self):
        result = _extract_tool_name("some tool output here")
        assert result == "some tool output here"

    def test_extract_tool_name_empty(self):
        assert _extract_tool_name("") == "Tool"


# ── API Tests ──────────────────────────────────────────────────────────


@pytest.fixture
async def app_with_client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_export_html.db"

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
    """Client + conversa com mensagens."""
    client = app_with_client

    resp = await client.post("/api/conversations", json={"model": "llama3.1:8b"})
    assert resp.status_code == 200
    conv_id = resp.json()["id"]

    async with get_db() as db:
        now = datetime.now().isoformat()
        messages = [
            (
                str(uuid.uuid4())[:12],
                conv_id,
                "user",
                "Qual a capital do Brasil?",
                now,
            ),
            (
                str(uuid.uuid4())[:12],
                conv_id,
                "assistant",
                "A capital do Brasil é Brasília.",
                now,
            ),
        ]
        await db.executemany(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            messages,
        )
        await db.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            ("Capital do Brasil", conv_id),
        )
        await db.commit()

    return client, conv_id


@pytest.mark.asyncio
class TestExportHtmlAPI:
    """Test HTML export via API."""

    async def test_export_html_not_found(self, app_with_client):
        resp = await app_with_client.get("/api/conversations/nonexistent/export?format=html")
        assert resp.status_code == 404

    async def test_export_html_returns_200(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert resp.status_code == 200

    async def test_export_html_content_type(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert "text/html" in resp.headers.get("content-type", "")

    async def test_export_html_has_doctype(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert "<!DOCTYPE html>" in resp.text

    async def test_export_html_has_title(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert "Capital do Brasil" in resp.text

    async def test_export_html_has_messages(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert "capital do Brasil" in resp.text
        assert "Brasília" in resp.text

    async def test_export_html_has_content_disposition(self, client_with_conversation):
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".html" in cd

    async def test_export_html_is_standalone(self, client_with_conversation):
        """HTML file should be self-contained with embedded CSS."""
        client, conv_id = client_with_conversation
        resp = await client.get(f"/api/conversations/{conv_id}/export?format=html")
        assert "<style>" in resp.text
        assert "</style>" in resp.text
        assert "var(--bg)" in resp.text
