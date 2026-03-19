"""Operações de arquivo — file_read, file_write, list_files."""

from pathlib import Path

from ..security.sandbox import BLOCKED_PATHS, is_path_allowed

# ─── Specs ─────────────────────────────────────────────────────────────────

FILE_READ_SPEC = {
    "type": "function",
    "function": {
        "name": "file_read",
        "description": "Lê o conteúdo de um arquivo dentro do diretório home do usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo (dentro do home)"}
            },
            "required": ["path"],
        },
    },
}

FILE_WRITE_SPEC = {
    "type": "function",
    "function": {
        "name": "file_write",
        "description": "Escreve conteúdo em um arquivo dentro do diretório home do usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do arquivo (dentro do home)"},
                "content": {"type": "string", "description": "Conteúdo para escrever"},
            },
            "required": ["path", "content"],
        },
    },
}

LIST_FILES_SPEC = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "Lista arquivos e pastas em um diretório dentro do home do usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Caminho do diretório (dentro do home)"},
                "pattern": {"type": "string", "description": "Padrão glob (ex: *.py)"},
            },
            "required": ["path"],
        },
    },
}

TOOLS = [
    (FILE_READ_SPEC, "file_read"),
    (FILE_WRITE_SPEC, "file_write"),
    (LIST_FILES_SPEC, "list_files"),
]


# ─── Executors ─────────────────────────────────────────────────────────────

async def file_read(args: dict) -> str:
    path_str = args["path"]
    allowed, reason = is_path_allowed(path_str)
    if not allowed:
        return f"🔒 {reason}"

    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        return f"❌ Arquivo não encontrado: {path}"
    if not path.is_file():
        return f"❌ Não é um arquivo: {path}"
    if path.stat().st_size > 500_000:
        return f"⚠️ Arquivo muito grande ({path.stat().st_size:,} bytes). Lendo primeiros 10000 chars."

    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > 10_000:
        text = text[:10_000] + f"\n\n... (truncado, {len(text):,} chars total)"
    return text


async def file_write(args: dict) -> str:
    path_str = args["path"]
    allowed, reason = is_path_allowed(path_str, write=True)
    if not allowed:
        return f"🔒 {reason}"

    path = Path(path_str).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"✅ Arquivo salvo: {path} ({len(args['content']):,} chars)"


async def list_files(args: dict) -> str:
    path_str = args["path"]
    allowed, reason = is_path_allowed(path_str)
    if not allowed:
        return f"🔒 {reason}"

    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        return f"❌ Diretório não encontrado: {path}"

    pattern = args.get("pattern", "*")
    files = sorted(path.glob(pattern))[:50]
    entries = []
    home = Path.home()

    for f in files:
        try:
            rel = str(f.relative_to(home))
            if any(rel.startswith(b) for b in BLOCKED_PATHS):
                continue
        except ValueError:
            continue

        if f.is_dir():
            entries.append(f"📁 {f.name}/")
        else:
            size = f.stat().st_size
            if size < 1024:
                s = f"{size} B"
            elif size < 1024 * 1024:
                s = f"{size // 1024} KB"
            else:
                s = f"{size // (1024 * 1024)} MB"
            entries.append(f"📄 {f.name} ({s})")

    return "\n".join(entries) if entries else "Diretório vazio."
