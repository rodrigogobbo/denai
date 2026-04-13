"""Testes para o endpoint de feedback (/api/feedback)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL


@pytest.fixture
async def client(tmp_path):
    db_path = tmp_path / "test.db"
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
        patch("denai.routes.feedback.FEEDBACK_DIR", tmp_path / "feedback"),
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


# ── GET /api/feedback/config ───────────────────────────────────────────────


class TestFeedbackConfig:
    @pytest.mark.asyncio
    async def test_config_no_token(self, client):
        with patch("denai.routes.feedback._get_feedback_config", return_value={}):
            resp = await client.get("/api/feedback/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True
        assert data["method"] == "local"
        assert data["has_token"] is False

    @pytest.mark.asyncio
    async def test_config_with_token(self, client):
        with patch(
            "denai.routes.feedback._get_feedback_config",
            return_value={"github_token": "ghp_test123", "repo": "user/repo"},
        ):
            resp = await client.get("/api/feedback/config")
        data = resp.json()
        assert data["method"] == "github"
        assert data["has_token"] is True
        assert data["repo"] == "user/repo"


# ── POST /api/feedback ─────────────────────────────────────────────────────


class TestSubmitFeedback:
    @pytest.mark.asyncio
    async def test_submit_saves_locally_no_token(self, client, tmp_path):
        with (
            patch("denai.routes.feedback._get_feedback_config", return_value={}),
            patch("denai.routes.feedback._collect_context", return_value={}),
            patch("denai.routes.feedback._get_recent_logs", return_value="log line"),
        ):
            resp = await client.post(
                "/api/feedback",
                json={
                    "type": "bug",
                    "title": "Botão não funciona",
                    "description": "Ao clicar no botão X nada acontece.",
                    "include_context": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "local"
        assert "file" in data

    @pytest.mark.asyncio
    async def test_submit_opens_github_issue(self, client):
        mock_response = {
            "method": "github",
            "issue_number": 42,
            "issue_url": "https://github.com/r/d/issues/42",
            "message": "Issue #42 aberta com sucesso!",
        }

        with (
            patch(
                "denai.routes.feedback._get_feedback_config", return_value={"github_token": "ghp_test", "repo": "r/d"}
            ),
            patch("denai.routes.feedback._submit_to_github", new_callable=AsyncMock, return_value=mock_response),
            patch("denai.routes.feedback._collect_context", return_value={}),
            patch("denai.routes.feedback._get_recent_logs", return_value=""),
        ):
            resp = await client.post(
                "/api/feedback",
                json={
                    "type": "bug",
                    "title": "Crash ao iniciar",
                    "description": "O DenAI crasha ao iniciar com Python 3.12.",
                    "include_context": True,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["issue_number"] == 42
        assert data["issue_url"].startswith("https://github.com")

    @pytest.mark.asyncio
    async def test_submit_fallback_on_github_error(self, client, tmp_path):
        with (
            patch("denai.routes.feedback._get_feedback_config", return_value={"github_token": "ghp_bad"}),
            patch("denai.routes.feedback._submit_to_github", side_effect=RuntimeError("GitHub API error")),
            patch("denai.routes.feedback._collect_context", return_value={}),
            patch("denai.routes.feedback._get_recent_logs", return_value=""),
        ):
            resp = await client.post(
                "/api/feedback",
                json={
                    "type": "improvement",
                    "title": "Suporte a múltiplos temas",
                    "description": "Seria ótimo ter mais opções de tema além de dark/light.",
                    "include_context": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "local"

    @pytest.mark.asyncio
    async def test_title_too_short(self, client):
        resp = await client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "ab",
                "description": "Descrição longa o suficiente.",
                "include_context": False,
            },
        )
        assert resp.status_code == 400
        assert "curto" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_description_too_short(self, client):
        resp = await client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Título OK",
                "description": "curto",
                "include_context": False,
            },
        )
        assert resp.status_code == 400
        assert "curta" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_invalid_type(self, client):
        resp = await client.post(
            "/api/feedback",
            json={
                "type": "invalid",
                "title": "Título OK",
                "description": "Descrição suficientemente longa.",
                "include_context": False,
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_improvement_type_works(self, client, tmp_path):
        with (
            patch("denai.routes.feedback._get_feedback_config", return_value={}),
            patch("denai.routes.feedback._collect_context", return_value={}),
        ):
            resp = await client.post(
                "/api/feedback",
                json={
                    "type": "improvement",
                    "title": "Adicionar modo escuro automático",
                    "description": "O tema deveria mudar automaticamente com o sistema operacional.",
                    "include_context": False,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] == "local"


# ── GET /api/feedback/list ─────────────────────────────────────────────────


class TestFeedbackList:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        resp = await client.get("/api/feedback/list")
        assert resp.status_code == 200
        assert resp.json()["feedbacks"] == []

    @pytest.mark.asyncio
    async def test_list_after_submit(self, client, tmp_path):
        with (
            patch("denai.routes.feedback._get_feedback_config", return_value={}),
            patch("denai.routes.feedback._collect_context", return_value={}),
            patch("denai.routes.feedback._get_recent_logs", return_value=""),
        ):
            await client.post(
                "/api/feedback",
                json={
                    "type": "bug",
                    "title": "Teste de listagem",
                    "description": "Verificando se feedback aparece na lista.",
                    "include_context": False,
                },
            )
        resp = await client.get("/api/feedback/list")
        data = resp.json()
        assert len(data["feedbacks"]) >= 1
        assert data["feedbacks"][0]["title"] == "Teste de listagem"


# ── _format_issue_body ────────────────────────────────────────────────────


class TestFormatIssueBody:
    def test_includes_description(self):
        from denai.routes.feedback import _format_issue_body

        body = _format_issue_body("Meu bug", "bug", None, None)
        assert "Meu bug" in body

    def test_includes_context(self):
        from denai.routes.feedback import _format_issue_body

        ctx = {"denai_version": "0.18.0", "os": "Linux x86_64", "python": "3.12", "ollama": "online"}
        body = _format_issue_body("desc", "bug", ctx, None)
        assert "0.18.0" in body
        assert "Linux" in body

    def test_includes_logs_for_bugs(self):
        from denai.routes.feedback import _format_issue_body

        body = _format_issue_body("desc", "bug", None, "ERROR linha de log")
        assert "ERROR linha de log" in body

    def test_no_logs_for_improvements(self):
        from denai.routes.feedback import _format_issue_body

        body = _format_issue_body("desc", "improvement", None, "log info")
        assert "log info" not in body

    def test_footer_present(self):
        from denai.routes.feedback import _format_issue_body

        body = _format_issue_body("desc", "bug", None, None)
        assert "DenAI in-app feedback" in body
