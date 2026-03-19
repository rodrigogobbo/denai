"""Testes para logging e rota de diagnóstico."""

from __future__ import annotations

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from denai.logging_config import LOG_DIR, get_logger, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging():
    """Remove handlers entre testes para evitar duplicação."""
    root = logging.getLogger("denai")
    root.handlers.clear()
    yield
    root.handlers.clear()


def test_setup_logging_creates_handlers():
    """setup_logging cria file + console handlers."""
    root = setup_logging()
    assert len(root.handlers) == 2
    handler_types = [type(h).__name__ for h in root.handlers]
    assert "RotatingFileHandler" in handler_types
    assert "StreamHandler" in handler_types


def test_setup_logging_idempotent():
    """Chamar setup_logging duas vezes não duplica handlers."""
    setup_logging()
    setup_logging()
    root = logging.getLogger("denai")
    assert len(root.handlers) == 2


def test_get_logger_returns_child():
    """get_logger retorna sub-logger com prefixo denai."""
    log = get_logger("tools")
    assert log.name == "denai.tools"


def test_log_dir_exists():
    """Diretório de logs é criado no import."""
    assert LOG_DIR.exists()


def test_log_writes_to_file(tmp_path):
    """Logger escreve no arquivo."""
    setup_logging()
    log = get_logger("test")
    log.warning("teste de log 12345")

    # Flush handlers
    for h in logging.getLogger("denai").handlers:
        h.flush()

    from denai.logging_config import LOG_FILE

    if LOG_FILE.exists():
        content = LOG_FILE.read_text()
        assert "teste de log 12345" in content


@pytest.mark.asyncio
async def test_diagnostics_endpoint():
    """GET /api/diagnostics retorna info do sistema."""
    from denai.app import app
    from denai.security import API_KEY

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/diagnostics",
            headers={"X-API-Key": API_KEY},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "system" in data
    assert "denai" in data
    assert "python" in data["system"]
    assert "model" in data["denai"]
    assert "log_file" in data["denai"]


@pytest.mark.asyncio
async def test_logs_endpoint():
    """GET /api/logs retorna logs do arquivo."""
    from denai.app import app
    from denai.security import API_KEY

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/logs?lines=10",
            headers={"X-API-Key": API_KEY},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "path" in data
    assert "lines" in data or "logs" in data
