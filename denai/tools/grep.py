"""Tool de busca em arquivos — grep com regex."""

from __future__ import annotations

import re
from pathlib import Path

from ..security.sandbox import is_path_allowed

# ─── Spec ──────────────────────────────────────────────────────────────────

GREP_SPEC = {
    "type": "function",
    "function": {
        "name": "grep",
        "description": (
            "Busca por padrão regex em arquivos de um diretório. "
            "Retorna linhas que contêm o padrão, com número da linha e nome do arquivo. "
            "Ideal para encontrar onde algo é definido ou usado no código."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex para buscar (ex: 'def main', 'TODO', 'import os')",
                },
                "path": {
                    "type": "string",
                    "description": "Diretório onde buscar (padrão: home do usuário)",
                },
                "include": {
                    "type": "string",
                    "description": "Glob para filtrar arquivos (ex: '*.py', '*.{js,ts}')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Máximo de resultados (padrão: 50)",
                },
            },
            "required": ["pattern"],
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


# Diretórios a ignorar na busca
_SKIP_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv",
    "venv", ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info",
}


def _should_skip_dir(name: str) -> bool:
    """Verifica se diretório deve ser ignorado."""
    return name in _SKIP_DIRS or name.endswith(".egg-info")


def _iter_files(root: Path, include: str = "") -> list[Path]:
    """Itera arquivos do diretório, respeitando filtros."""
    files = []
    if include:
        # Expandir patterns como *.{py,js} manualmente
        patterns = []
        if "{" in include and "}" in include:
            # Ex: *.{py,js,ts} → ['*.py', '*.js', '*.ts']
            prefix, rest = include.split("{", 1)
            extensions, suffix = rest.split("}", 1)
            for ext in extensions.split(","):
                patterns.append(f"{prefix}{ext.strip()}{suffix}")
        else:
            patterns = [include]

        for pat in patterns:
            for f in root.rglob(pat):
                if f.is_file() and not any(_should_skip_dir(p) for p in f.relative_to(root).parts[:-1]):
                    files.append(f)
    else:
        for f in root.rglob("*"):
            if f.is_file() and not any(_should_skip_dir(p) for p in f.relative_to(root).parts[:-1]):
                files.append(f)
    return sorted(set(files))


# ─── Executor ──────────────────────────────────────────────────────────────


async def grep(args: dict) -> str:
    """Busca padrão regex em arquivos."""
    pattern_str = args.get("pattern", "")
    if not pattern_str:
        return "❌ Parâmetro 'pattern' é obrigatório."

    path_str = args.get("path", str(Path.home()))
    include = args.get("include", "")
    max_results = min(int(args.get("max_results", 50)), 200)

    root = _resolve_path(path_str)

    allowed, reason = is_path_allowed(str(root))
    if not allowed:
        return f"🔒 {reason}"

    if not root.exists():
        return f"❌ Diretório não encontrado: {root}"
    if not root.is_dir():
        return f"❌ Não é um diretório: {root}"

    try:
        regex = re.compile(pattern_str, re.IGNORECASE)
    except re.error as e:
        return f"❌ Regex inválido: {e}"

    files = _iter_files(root, include)
    results = []
    files_searched = 0

    for fpath in files:
        if len(results) >= max_results:
            break
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
            files_searched += 1
        except Exception:
            continue

        for line_num, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                # Caminho relativo ao root
                try:
                    rel = fpath.relative_to(root)
                except ValueError:
                    rel = fpath
                results.append(f"  {rel}:{line_num} | {line.rstrip()[:200]}")
                if len(results) >= max_results:
                    break

    if not results:
        return f"🔍 Nenhum resultado para /{pattern_str}/ em {root} ({files_searched} arquivo(s))"

    header = f"🔍 {len(results)} resultado(s) para /{pattern_str}/ ({files_searched} arquivo(s))"
    if len(results) >= max_results:
        header += f" — limitado a {max_results}"

    return header + "\n" + "\n".join(results)


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (GREP_SPEC, "grep"),
]
