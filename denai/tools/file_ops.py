"""Tools de filesystem — ler, escrever, listar e editar arquivos com backup automático."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from ..config import DATA_DIR
from ..security.sandbox import is_path_allowed
from ..undo import save_snapshot

# ─── Backup ────────────────────────────────────────────────────────────────

BACKUP_DIR = DATA_DIR / "backups"


def _create_backup(path: Path) -> str | None:
    """Cria backup de um arquivo antes de modificá-lo. Retorna caminho do backup ou None."""
    if not path.exists() or not path.is_file():
        return None
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"{ts}_{path.name}"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(str(path), str(backup_path))
        return str(backup_path)
    except Exception:
        return None  # Backup é best-effort — não impede a operação


# ─── Specs ─────────────────────────────────────────────────────────────────

FILE_READ_SPEC = {
    "type": "function",
    "function": {
        "name": "file_read",
        "description": (
            "Lê o conteúdo de um arquivo. Retorna o texto com números de linha. "
            "Suporta offset e limit para arquivos grandes. "
            "SEMPRE use file_read antes de file_edit para ver o conteúdo atual."
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
            "Escreve conteúdo em um arquivo, criando diretórios se necessário. "
            "SOBRESCREVE o arquivo inteiro se já existir (backup automático). "
            "Prefira file_edit para mudanças cirúrgicas em arquivos existentes."
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
    """Escreve conteúdo em arquivo com backup automático."""
    path_str = args.get("path", "")
    content = args.get("content", "")

    if not path_str:
        return "❌ Parâmetro 'path' é obrigatório."

    path = _resolve_path(path_str)

    err = _check_sandbox(str(path), write=True)
    if err:
        return err

    try:
        # Backup antes de sobrescrever
        backup = _create_backup(path)

        # Snapshot para undo (antes de modificar)
        save_snapshot(str(path))

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        size = path.stat().st_size
        msg = f"✅ Arquivo salvo: {path} ({size} bytes)"
        if backup:
            msg += f"\n💾 Backup: {backup}"
        return msg
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
        entries = sorted(path.glob(pattern)) if pattern else sorted(path.iterdir())
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


# ─── file_edit ─────────────────────────────────────────────────────────────

FILE_EDIT_SPEC = {
    "type": "function",
    "function": {
        "name": "file_edit",
        "description": (
            "Edita um arquivo substituindo um trecho de texto por outro. "
            "Funciona como search-and-replace exato (backup automático). "
            "IMPORTANTE: Sempre use file_read antes para ver o conteúdo atual."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Caminho do arquivo a editar",
                },
                "old_text": {
                    "type": "string",
                    "description": "Texto exato a ser encontrado e substituído",
                },
                "new_text": {
                    "type": "string",
                    "description": "Texto substituto",
                },
                "replace_all": {
                    "type": "boolean",
                    "description": "Substituir todas as ocorrências (padrão: false, só a primeira)",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
}


async def file_edit(args: dict) -> str:
    """Substitui trecho de texto em arquivo (search/replace exato) com backup."""
    path_str = args.get("path", "")
    old_text = args.get("old_text", "")
    new_text = args.get("new_text", "")
    replace_all = args.get("replace_all", False)

    if not path_str:
        return "❌ Parâmetro 'path' é obrigatório."
    if not old_text:
        return "❌ Parâmetro 'old_text' é obrigatório."

    path = _resolve_path(path_str)

    err = _check_sandbox(str(path), write=True)
    if err:
        return err

    if not path.exists():
        return f"❌ Arquivo não encontrado: {path}"
    if not path.is_file():
        return f"❌ Não é um arquivo: {path}"

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"❌ Erro ao ler: {e}"

    # Contar ocorrências
    count = content.count(old_text)
    if count == 0:
        # Mostrar contexto para ajudar a debugar
        preview = old_text[:80].replace("\n", "\\n")
        return f'❌ Texto não encontrado no arquivo.\nBuscado: "{preview}"\nArquivo: {path}'

    # Backup antes de editar
    _create_backup(path)

    # Snapshot para undo (antes de modificar)
    save_snapshot(str(path))

    # Substituir
    if replace_all:
        new_content = content.replace(old_text, new_text)
        replaced = count
    else:
        new_content = content.replace(old_text, new_text, 1)
        replaced = 1

    try:
        path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        return f"❌ Erro ao escrever: {e}"

    return f"✅ {replaced} substituição(ões) em {path.name}"


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (FILE_READ_SPEC, "file_read"),
    (FILE_WRITE_SPEC, "file_write"),
    (LIST_FILES_SPEC, "list_files"),
    (FILE_EDIT_SPEC, "file_edit"),
]
