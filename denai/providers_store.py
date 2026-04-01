"""Persistência de providers em ~/.denai/providers.yaml.

Providers são salvos/carregados independente do config.yaml.
API keys são salvas localmente mas NUNCA expostas via API (retornam "***").
O arquivo é criado com permissão 600 (apenas o dono pode ler).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("providers_store")

PROVIDERS_FILE = DATA_DIR / "providers.yaml"

# ─── Templates pré-configurados ────────────────────────────────────────────

PROVIDER_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "openai",
        "label": "OpenAI",
        "description": "GPT-4o, GPT-4o mini, o1 — API oficial da OpenAI",
        "kind": "openai",
        "base_url": "https://api.openai.com",
        "requires_key": True,
        "default_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"],
    },
    {
        "id": "anthropic",
        "label": "Anthropic (Claude)",
        "description": "Claude 3.5 Sonnet, Claude 3 Haiku — via endpoint OpenAI-compat",
        "kind": "openai",
        "base_url": "https://api.anthropic.com/v1",
        "requires_key": True,
        "default_models": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        "extra_headers": {"anthropic-version": "2023-06-01"},
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "description": "Gemini 2.0 Flash, Gemini Pro — via endpoint OpenAI-compat",
        "kind": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "requires_key": True,
        "default_models": [
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
    },
    {
        "id": "openrouter",
        "label": "OpenRouter",
        "description": "Acesso a centenas de modelos (Llama, Mistral, Claude, GPT...) via uma API",
        "kind": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "default_models": [
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
        ],
    },
    {
        "id": "groq",
        "label": "Groq",
        "description": "Inferência ultra-rápida — Llama 3, Mixtral, Gemma",
        "kind": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "requires_key": True,
        "default_models": [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ],
    },
    {
        "id": "lmstudio",
        "label": "LM Studio",
        "description": "Modelos locais via LM Studio (roda na sua máquina)",
        "kind": "openai",
        "base_url": "http://localhost:1234",
        "requires_key": False,
        "default_models": [],
    },
    {
        "id": "localai",
        "label": "LocalAI",
        "description": "Modelos locais via LocalAI — compatível com OpenAI API",
        "kind": "openai",
        "base_url": "http://localhost:8080",
        "requires_key": False,
        "default_models": [],
    },
    {
        "id": "ollama_custom",
        "label": "Ollama (remoto)",
        "description": "Instância Ollama em outro endereço ou servidor",
        "kind": "ollama",
        "base_url": "http://localhost:11434",
        "requires_key": False,
        "default_models": [],
    },
]


# ─── Load / Save ────────────────────────────────────────────────────────────


def _ensure_secure_file(path: Path) -> None:
    """Garante que o arquivo existe com permissão 600 (dono apenas)."""
    if not path.exists():
        path.touch(mode=0o600)
    else:
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass  # Windows não suporta — ignora silenciosamente


def load_providers() -> list[dict[str, Any]]:
    """Carrega providers do arquivo de persistência."""
    if not PROVIDERS_FILE.exists():
        return []
    try:
        content = PROVIDERS_FILE.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if isinstance(data, dict):
            return data.get("providers", [])
        return []
    except Exception as e:
        log.warning("Erro ao carregar providers.yaml: %s", e)
        return []


def save_providers(providers: list[dict[str, Any]]) -> None:
    """Salva lista de providers no arquivo de persistência."""
    PROVIDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ensure_secure_file(PROVIDERS_FILE)
    try:
        content = yaml.dump(
            {"providers": providers},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )
        PROVIDERS_FILE.write_text(content, encoding="utf-8")
    except Exception as e:
        log.error("Erro ao salvar providers.yaml: %s", e)


def add_or_update_provider(provider_data: dict[str, Any]) -> None:
    """Adiciona ou atualiza um provider pelo nome."""
    providers = load_providers()
    name = provider_data["name"].lower()
    existing = next((i for i, p in enumerate(providers) if p.get("name", "").lower() == name), None)
    if existing is not None:
        providers[existing] = provider_data
    else:
        providers.append(provider_data)
    save_providers(providers)


def remove_provider(name: str) -> bool:
    """Remove um provider pelo nome. Retorna True se existia."""
    providers = load_providers()
    original_len = len(providers)
    providers = [p for p in providers if p.get("name", "").lower() != name.lower()]
    if len(providers) < original_len:
        save_providers(providers)
        return True
    return False


def mask_api_key(key: str) -> str:
    """Mascara API key para exibição — nunca expor o valor real."""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-2:]
