"""Sandbox de arquivos — restringe acesso ao home do usuário."""

from pathlib import Path

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


def is_path_allowed(path_str: str, write: bool = False) -> tuple:
    """Verifica se o caminho está dentro do sandbox.

    Returns:
        (allowed, reason) — reason vazio se permitido.
    """
    try:
        path = Path(path_str).expanduser().resolve()
    except (ValueError, OSError):
        return False, "Caminho inválido"

    home = Path.home().resolve()
    try:
        path.relative_to(home)
    except ValueError:
        return False, f"Acesso negado: só é permitido acessar arquivos dentro de {home}"

    # Normalizar pra forward slash pra comparação cross-platform
    rel = path.relative_to(home).as_posix()
    for blocked in BLOCKED_PATHS:
        if rel == blocked or rel.startswith(blocked + "/"):
            return False, f"Acesso negado: {blocked} é protegido por segurança"

    return True, ""
