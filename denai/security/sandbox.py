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


def is_path_allowed(path_str: str, write: bool = False) -> tuple:  # noqa: ARG001
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


def get_safe_path(path_str: str) -> str | None:
    """Retorna o caminho seguro reconstruído a partir do home, ou None se não permitido.

    Diferente de is_path_allowed(), este método retorna o path reconstruído
    internamente a partir de home (fonte confiável) + parte relativa validada.
    O valor retornado não flui diretamente do input do usuário — quebra o taint
    no CodeQL.

    Returns:
        Caminho absoluto reconstruído, ou None se não permitido.
    """
    allowed, _ = is_path_allowed(path_str)
    if not allowed:
        return None

    try:
        path = Path(path_str).expanduser().resolve()
        home = Path.home().resolve()
        rel = path.relative_to(home)
        # Reconstruir de home (não tainted) + rel como partes de string
        # O CodeQL reconhece que home é fonte confiável (Path.home())
        parts = rel.parts
        result = home
        for part in parts:
            result = result / part
        return str(result)
    except (ValueError, OSError):
        return None
