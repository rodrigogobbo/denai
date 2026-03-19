"""Tools de filesystem — ler, escrever e listar arquivos."""

from __future__ import annotations

from pathlib import Path

from ..security.sandbox import is_path_allowed

# ─── Specs ─────────────────────────────────────────────────────────────────

FILE_READ_SPEC = {
    "type": "function",
    "function": {
        "name": "file_read",
        "description": (
            "Lê o conteúdo de um arquivo. Retorna o texto com números de linha. "
            "Suporta offset e limit para arquivos grandes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho absoluto ou relativo ao home do arquivo",
                },
                "offset": {
                    "type": "integer",
                    "description": "Linha inicial (0-based, padrão: 0)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de linhas (padrão: 200)",
                },
            },
            "required": ["path"],
        },
    },
}

FILE_WRITE_SPEC = {
    "type": "function",
    "function": {
        "name": "file_write",
        "description": (
            "Escreve conteúdo em um arquivo, criando diretórios se necessário. Sobrescreve o arquivo se já existir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho absoluto ou relativo ao home do arquivo",
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo a ser escrito no arquivo",
                },
            },
            "required": ["path", "content"],
        },
    },
}

LIST_FILES_SPEC = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": ("Lista arquivos e diretórios em um caminho. Suporta glob patterns (ex: *.py, **/*.md)."),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Diretório a listar (padrão: home do usuário)",
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern para filtrar (ex: *.py, **/*.md)",
                },
            },
        },
    },
}


# ─── Helpers ───────────────────────────────────────────────────────────────


def _resolve_path(path_str: str) -> Path:
    """Resolve ~ e caminhos relativos."""
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p.resolve()


def _check_sandbox(path_str: str, write: bool = False) -> str | None:
    """Retorna mensagem de erro se path bloqueado, None se OK."""
    allowed, reason = is_path_allowed(path_str, write=write)
    if not allowed:
        return f"🔒 {reason}"
    return None


# ─── Executors ─────────────────────────────────────────────────────────────


async def file_read(args: dict) -> str:
    """Lê arquivo com números de linha."""
    path_str = args.get("path", "")
    if not path_str:
        return "❌ Parâmetro 'path' é obrigatório."

    path = _resolve_path(path_str)

    err = _check_sandbox(str(path))
    if err:
        return err

    if not path.exists():
        return f"❌ Arquivo não encontrado: {path}"
    if not path.is_file():
        return f"❌ Não é um arquivo: {path}"

    offset = int(args.get("offset", 0))
    limit = int(args.get("limit", 200))

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Erro ao ler: {e}"

    lines = text.splitlines()
    total = len(lines)
    selected = lines[offset : offset + limit]

    parts = []
    for i, line in enumerate(selected, start=offset + 1):
        parts.append(f"{i:>4} | {line}")

    header = f"📄 {path.name} ({total} linhas)"
    if total > len(selected):
        header += f" — mostrando {offset + 1}-{offset + len(selected)}"

    return header + "\n" + "\n".join(parts)


async def file_write(args: dict) -> str:
    """Escreve conteúdo em arquivo."""
    path_str = args.get("path", "")
    content = args.get("content", "")

    if not path_str:
        return "❌ Parâmetro 'path' é obrigatório."

    path = _resolve_path(path_str)

    err = _check_sandbox(str(path), write=True)
    if err:
        return err

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        size = path.stat().st_size
        return f"✅ Arquivo salvo: {path} ({size} bytes)"
    except Exception as e:
        return f"❌ Erro ao escrever: {e}"


async def list_files(args: dict) -> str:
    """Lista arquivos de um diretório."""
    path_str = args.get("path", str(Path.home()))
    pattern = args.get("pattern", "")

    path = _resolve_path(path_str)

    err = _check_sandbox(str(path))
    if err:
        return err

    if not path.exists():
        return f"❌ Diretório não encontrado: {path}"
    if not path.is_dir():
        return f"❌ Não é um diretório: {path}"

    try:
        if pattern:
            entries = sorted(path.glob(pattern))
        else:
            entries = sorted(path.iterdir())
    except Exception as e:
        return f"❌ Erro ao listar: {e}"

    if not entries:
        msg = f"📂 {path} — vazio"
        if pattern:
            msg += f" (pattern: {pattern})"
        return msg

    # Limitar a 100 entradas
    total = len(entries)
    entries = entries[:100]

    parts = [f"📂 {path} ({total} item(s))"]
    if pattern:
        parts[0] += f" [pattern: {pattern}]"

    for entry in entries:
        if entry.is_dir():
            parts.append(f"  📁 {entry.name}/")
        else:
            try:
                size = entry.stat().st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
            except OSError:
                size_str = "?"
            parts.append(f"  📄 {entry.name} ({size_str})")

    if total > 100:
        parts.append(f"  ... e mais {total - 100} item(s)")

    return "\n".join(parts)


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (FILE_READ_SPEC, "file_read"),
    (FILE_WRITE_SPEC, "file_write"),
    (LIST_FILES_SPEC, "list_files"),
]
