"""Testes do módulo de voz."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import create_app
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


# ── Status ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_voice_status_unavailable(client):
    """Whisper não está instalado no CI — deve retornar available=False."""
    resp = await client.get("/api/voice/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False


# ── Transcribe without Whisper ────────────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_without_whisper(client):
    """Sem Whisper, retorna erro amigável."""
    audio = b"fake audio data"
    resp = await client.post(
        "/api/voice/transcribe",
        files={"audio": ("test.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert "Whisper" in data["error"]
    assert data["text"] == ""


# ── File size limit ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_file_too_large(client):
    """Arquivo > 25MB é rejeitado."""
    # Mock whisper as available so we hit the size check
    with patch("denai.routes.voice.WHISPER_AVAILABLE", True):
        big_audio = b"x" * (26 * 1024 * 1024)
        resp = await client.post(
            "/api/voice/transcribe",
            files={"audio": ("big.wav", big_audio, "audio/wav")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert "25MB" in data["error"]


# ── Successful transcription (mocked) ────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_success_mocked(client):
    """Com whisper mockado, transcrição funciona."""
    mock_result = {"text": " Olá, mundo! ", "language": "pt"}

    with (
        patch("denai.routes.voice.WHISPER_AVAILABLE", True),
        patch("denai.voice.WHISPER_AVAILABLE", True),
        patch("denai.voice.get_whisper_model") as mock_model,
    ):
        mock_model.return_value.transcribe.return_value = mock_result
        audio = b"fake wav data for testing"
        resp = await client.post(
            "/api/voice/transcribe",
            files={"audio": ("test.wav", audio, "audio/wav")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Olá, mundo!"
        assert data["language"] == "pt"


# ── Voice module unit tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_transcribe_function_no_whisper():
    """transcribe() sem whisper retorna erro."""
    from denai.voice import transcribe

    # whisper is not installed in test env
    result = await transcribe(b"audio data")
    assert "error" in result
    assert result["text"] == ""


def test_whisper_available_flag():
    """WHISPER_AVAILABLE deve ser False no ambiente de teste."""
    from denai.voice import WHISPER_AVAILABLE

    assert WHISPER_AVAILABLE is False
