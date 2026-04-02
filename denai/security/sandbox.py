"""Sandbox de arquivos — restringe acesso ao home do usuário."""

from __future__ import annotations

import os

# Paths proibidos mesmo dentro do home (sempre com / como separador)
BLOCKED_PATHS = [
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".gcloud",
    ".kube",
    ".docker/config.json",
    ".denai/api.key",  # Protege a própria API key
    "AppData/Local/Google/Chrome/User Data",
    "AppData/Local/Microsoft/Edge/User Data",
    "Library/Keychains",  # macOS keychain
]

# Separador de path do sistema (para garantir match exato de prefixo)
_SEP = os.sep


def is_path_allowed(path_str: str, write: bool = False) -> tuple:  # noqa: ARG001
    """Verifica se o caminho está dentro do sandbox.

    Returns:
        (allowed, reason) — reason vazio se permitido.
    """
    # os.path.realpath + abspath é o padrão reconhecido pelo CodeQL como
    # sanitizador de path traversal quando seguido de verificação de prefixo.
    try:
        normalized = os.path.realpath(os.path.abspath(os.path.expanduser(path_str)))
    except (ValueError, OSError):
        return False, "Caminho inválido"

    home = os.path.realpath(os.path.expanduser("~"))

    # Verificação de prefixo — padrão reconhecido pelo CodeQL como sanitização
    if not (normalized == home or normalized.startswith(home + _SEP)):
        return False, f"Acesso negado: só é permitido acessar arquivos dentro de {home}"

    # Verificar blocked paths usando a parte relativa
    rel = normalized[len(home) + 1 :].replace("\\", "/")
    for blocked in BLOCKED_PATHS:
        if rel == blocked or rel.startswith(blocked + "/"):
            return False, f"Acesso negado: {blocked} é protegido por segurança"

    return True, ""


def get_safe_path(path_str: str) -> str | None:
    """Retorna o caminho normalizado e validado, ou None se não permitido.

    Usa os.path.realpath/abspath (sanitizador reconhecido pelo CodeQL)
    seguido de verificação de prefixo com o home do usuário.

    Returns:
        Caminho normalizado absoluto, ou None se fora do sandbox.
    """
    allowed, _ = is_path_allowed(path_str)
    if not allowed:
        return None

    try:
        # Após is_path_allowed confirmar, o valor normalizado é seguro.
        # O CodeQL reconhece realpath+abspath+startswith(home) como sanitização.
        normalized = os.path.realpath(os.path.abspath(os.path.expanduser(path_str)))
        home = os.path.realpath(os.path.expanduser("~"))
        if normalized == home or normalized.startswith(home + _SEP):
            return normalized
        return None
    except (ValueError, OSError):
        return None
