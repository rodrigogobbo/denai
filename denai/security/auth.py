"""Geração e validação de API Key + middleware de autenticação."""

from __future__ import annotations

import secrets

from ..config import API_KEY_PATH


def get_or_create_api_key() -> str:
    """Gera uma API key no primeiro boot e salva em ~/.denai/api.key."""
    if API_KEY_PATH.exists():
        key = API_KEY_PATH.read_text().strip()
        if len(key) >= 32:
            return key
    key = secrets.token_urlsafe(36)
    API_KEY_PATH.write_text(key)
    try:
        API_KEY_PATH.chmod(0o600)
    except OSError:
        pass  # Windows
    return key


API_KEY = get_or_create_api_key()

# Rotas públicas (sem auth)
PUBLIC_PATHS = {"/", "/api/health", "/favicon.ico"}


def verify_api_key(provided: str | None) -> bool:
    """Compara API key de forma timing-safe."""
    if not provided:
        return False
    return secrets.compare_digest(provided, API_KEY)
