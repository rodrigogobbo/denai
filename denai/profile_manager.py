"""Gerenciamento de perfis — namespaces isolados de dados.

Cada perfil tem seu próprio diretório com denai.db, config.yaml
e providers.yaml. O perfil 'default' usa ~/.denai/ diretamente
para retrocompatibilidade total.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .logging_config import get_logger

log = get_logger("profile_manager")

# ─── Constantes ────────────────────────────────────────────────────────────

_BASE_DIR = Path.home() / ".denai"
_PROFILES_DIR = _BASE_DIR / "profiles"
_ACTIVE_FILE = _BASE_DIR / "active_profile"

_VALID_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")


# ─── Helpers ───────────────────────────────────────────────────────────────


def _validate_name(name: str) -> None:
    if not _VALID_NAME.match(name):
        raise ValueError(f"Nome de perfil inválido: '{name}'. Use apenas letras, números, _ e - (máx 32 chars).")


# ─── Public API ────────────────────────────────────────────────────────────


def get_active_profile() -> str:
    """Retorna o nome do perfil ativo. Default: 'default'."""
    try:
        if _ACTIVE_FILE.exists():
            name = _ACTIVE_FILE.read_text(encoding="utf-8").strip()
            if name and _VALID_NAME.match(name):
                return name
    except Exception:
        pass
    return "default"


def set_active_profile(name: str) -> None:
    """Grava o perfil ativo. Cria o diretório se não existir."""
    _validate_name(name)
    if name != "default":
        get_profile_dir(name).mkdir(parents=True, exist_ok=True)
    _BASE_DIR.mkdir(parents=True, exist_ok=True)
    _ACTIVE_FILE.write_text(name, encoding="utf-8")
    log.info("Perfil ativo alterado")


def get_profile_dir(name: str) -> Path:
    """Retorna o diretório de dados do perfil.

    O perfil 'default' usa ~/.denai/ diretamente (retrocompatível).
    Os demais usam ~/.denai/profiles/<name>/.
    """
    if name == "default":
        return _BASE_DIR
    return _PROFILES_DIR / name


def list_profiles() -> list[dict]:
    """Lista todos os perfis disponíveis."""
    profiles = []
    active = get_active_profile()

    # Sempre inclui 'default'
    default_dir = _BASE_DIR
    profiles.append(
        {
            "name": "default",
            "active": active == "default",
            "dir": str(default_dir),
            "has_data": (default_dir / "denai.db").exists(),
        }
    )

    # Perfis customizados
    if _PROFILES_DIR.exists():
        for p in sorted(_PROFILES_DIR.iterdir()):
            if p.is_dir() and _VALID_NAME.match(p.name):
                profiles.append(
                    {
                        "name": p.name,
                        "active": active == p.name,
                        "dir": str(p),
                        "has_data": (p / "denai.db").exists(),
                    }
                )

    return profiles


def create_profile(name: str) -> Path:
    """Cria um novo perfil e retorna seu diretório."""
    _validate_name(name)
    if name == "default":
        raise ValueError("Não é possível criar um perfil chamado 'default'.")

    profile_dir = _PROFILES_DIR / name
    if profile_dir.exists():
        raise ValueError(f"Perfil '{name}' já existe.")

    profile_dir.mkdir(parents=True, exist_ok=True)
    log.info("Perfil criado com sucesso")
    return profile_dir


def delete_profile(name: str) -> bool:
    """Remove um perfil e seus dados. Não permite remover o ativo ou o default."""
    _validate_name(name)
    if name == "default":
        raise ValueError("Não é possível remover o perfil 'default'.")
    if name == get_active_profile():
        raise ValueError(f"Não é possível remover o perfil ativo '{name}'. Troque de perfil primeiro.")

    profile_dir = _PROFILES_DIR / name
    if not profile_dir.exists():
        return False

    shutil.rmtree(profile_dir)
    log.info("Perfil removido com sucesso")
    return True
