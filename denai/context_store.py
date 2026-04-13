"""Context store — estado de contexto de repositório por conversa.

Mantém em memória o índice BM25 e o sumário do projeto para cada
conversa que ativou o modo /context. Zerado ao reiniciar o servidor.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from .logging_config import get_logger
from .project import ProjectInfo, analyze_project
from .security.sandbox import is_path_allowed

log = get_logger("context_store")

# ─── Limites ───────────────────────────────────────────────────────────────

MAX_FILES = 500
MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50MB
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "venv",
    ".venv",
    "env",
    ".env",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
SKIP_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".lock",
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".whl",
    ".zip",
    ".tar",
    ".gz",
    ".egg-info",
    ".db",
    ".sqlite",
    ".sqlite3",
}

# ─── State ─────────────────────────────────────────────────────────────────

_contexts: dict[str, dict] = {}
# {conv_id: {path, project_name, summary, index, file_count}}


# ─── Gitignore parser ──────────────────────────────────────────────────────


def _load_gitignore_patterns(root: Path) -> list[str]:
    """Carrega padrões do .gitignore se existir."""
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns = []
    try:
        for line in gitignore.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line.rstrip("/"))
    except Exception:
        pass
    return patterns


def _is_ignored(path: Path, root: Path, gitignore: list[str]) -> bool:
    """Verifica se o path deve ser ignorado (gitignore simples)."""
    rel = path.relative_to(root).as_posix()
    name = path.name
    for pattern in gitignore:
        if pattern == name:
            return True
        if pattern == rel:
            return True
        if pattern.startswith("*") and rel.endswith(pattern[1:]):
            return True
        if rel.startswith(pattern + "/"):
            return True
    return False


# ─── Indexing ──────────────────────────────────────────────────────────────


def _collect_files(root: Path, gitignore: list[str]) -> list[Path]:
    """Coleta arquivos do diretório respeitando limites e filtros."""
    files = []
    total_size = 0

    for f in root.rglob("*"):
        if not f.is_file():
            continue
        # Pular diretórios proibidos
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        # Pular extensões binárias/desnecessárias
        if f.suffix.lower() in SKIP_EXTENSIONS:
            continue
        # Pular arquivos gitignored
        if gitignore and _is_ignored(f, root, gitignore):
            continue
        # Verificar tamanho do arquivo
        try:
            size = f.stat().st_size
        except OSError:
            continue
        if size == 0 or size > 500 * 1024:  # pular > 500KB individual
            continue
        total_size += size
        if total_size > MAX_SIZE_BYTES:
            log.warning("Context index: limite de tamanho atingido (%dMB)", MAX_SIZE_BYTES // (1024 * 1024))
            break
        files.append(f)
        if len(files) >= MAX_FILES:
            log.warning("Context index: limite de %d arquivos atingido", MAX_FILES)
            break

    return files


def _build_bm25_index(files: list[Path], root: Path) -> dict:
    """Constrói índice BM25 simples em memória."""
    k1, b = 1.5, 0.75
    docs: list[dict] = []
    df: dict[str, int] = {}

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel_path = str(f.relative_to(root))
        tokens = re.findall(r"\w+", text.lower())
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for t in tf:
            df[t] = df.get(t, 0) + 1
        docs.append({"path": rel_path, "text": text[:2000], "tf": tf, "len": len(tokens)})

    avg_len = sum(d["len"] for d in docs) / max(len(docs), 1)
    n = len(docs)

    return {"docs": docs, "df": df, "avg_len": avg_len, "n": n, "k1": k1, "b": b}


def _bm25_search(index: dict, query: str, top_k: int = 5) -> list[dict]:
    """Busca BM25 no índice."""
    if not index["docs"]:
        return []
    tokens = re.findall(r"\w+", query.lower())
    k1, b = index["k1"], index["b"]
    avg_len = index["avg_len"]
    n = index["n"]
    scores: list[tuple[float, dict]] = []

    for doc in index["docs"]:
        score = 0.0
        for t in tokens:
            tf = doc["tf"].get(t, 0)
            if tf == 0:
                continue
            df_t = index["df"].get(t, 0)
            idf = math.log((n - df_t + 0.5) / (df_t + 0.5) + 1)
            norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc["len"] / max(avg_len, 1)))
            score += idf * norm
        if score > 0:
            scores.append((score, doc))

    scores.sort(key=lambda x: x[0], reverse=True)
    return [{"path": d["path"], "snippet": d["text"][:500], "score": round(s, 3)} for s, d in scores[:top_k]]


# ─── Public API ────────────────────────────────────────────────────────────


def activate_context(conv_id: str, path: str) -> dict:
    """Indexa um diretório e ativa o contexto para a conversa."""
    # Validar path
    allowed, reason = is_path_allowed(path)
    if not allowed:
        return {"ok": False, "error": f"Caminho não permitido: {reason}"}

    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "error": "Caminho não é um diretório."}

    # Analisar projeto
    try:
        info = analyze_project(root)
    except Exception:
        info = ProjectInfo(path=str(root), name=root.name)

    # Indexar arquivos
    gitignore = _load_gitignore_patterns(root)
    files = _collect_files(root, gitignore)
    index = _build_bm25_index(files, root)

    summary = info.to_context() if info.languages else f"## Projeto: {info.name}\n**Caminho:** `{root}`"

    _contexts[conv_id] = {
        "path": str(root),
        "project_name": info.name,
        "summary": summary,
        "index": index,
        "file_count": len(files),
    }

    log.info("Context ativado para conv=%s: %d arquivos em %s", conv_id[:8], len(files), root.name)
    return {
        "ok": True,
        "project_name": info.name,
        "file_count": len(files),
        "summary_preview": summary[:200],
    }


def deactivate_context(conv_id: str) -> bool:
    """Remove o contexto da conversa."""
    if conv_id in _contexts:
        del _contexts[conv_id]
        return True
    return False


def get_context(conv_id: str) -> dict | None:
    """Retorna o contexto ativo de uma conversa."""
    return _contexts.get(conv_id)


def has_context(conv_id: str) -> bool:
    return conv_id in _contexts


def search_context(conv_id: str, query: str, top_k: int = 5) -> list[dict]:
    """Busca no índice de contexto da conversa."""
    ctx = _contexts.get(conv_id)
    if not ctx:
        return []
    return _bm25_search(ctx["index"], query, top_k)


def list_active_contexts() -> list[dict]:
    """Lista todos os contextos ativos (para debug/admin)."""
    return [
        {"conv_id": cid, "project": c["project_name"], "file_count": c["file_count"]} for cid, c in _contexts.items()
    ]
