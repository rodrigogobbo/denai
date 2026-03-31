"""Tools de memória persistente — salvar e buscar contexto entre sessões."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..config import DATA_DIR

# ─── Specs ─────────────────────────────────────────────────────────────────

MEMORY_SAVE_SPEC = {
    "type": "function",
    "function": {
        "name": "memory_save",
        "description": (
            "Salva uma informação na memória persistente. Use para lembrar "
            "fatos sobre o usuário, decisões tomadas, preferências, ou "
            "observações importantes que devem sobreviver entre conversas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "O que lembrar (seja conciso e específico)",
                },
                "type": {
                    "type": "string",
                    "enum": ["fact", "decision", "preference", "observation"],
                    "description": "Tipo da memória (padrão: observation)",
                },
                "tags": {
                    "type": "string",
                    "description": "Tags separadas por vírgula para categorização",
                },
            },
            "required": ["content"],
        },
    },
}

MEMORY_SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "memory_search",
        "description": (
            "Busca informações salvas na memória persistente. Use para "
            "recuperar contexto de conversas anteriores, preferências "
            "do usuário, ou decisões passadas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Palavras-chave para buscar nas memórias",
                },
                "type": {
                    "type": "string",
                    "enum": ["fact", "decision", "preference", "observation"],
                    "description": "Filtrar por tipo (opcional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 10)",
                },
            },
            "required": ["query"],
        },
    },
}


# ─── Database ──────────────────────────────────────────────────────────────

MEMORY_DB = DATA_DIR / "memory.db"


def _get_db() -> sqlite3.Connection:
    """Abre (e inicializa se necessário) o banco de memórias."""
    MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(MEMORY_DB))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'observation',
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """
    )
    # Index para busca por conteúdo
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memories_content
        ON memories(content)
    """
    )
    conn.commit()
    return conn


# ─── Executors ─────────────────────────────────────────────────────────────


async def memory_save(args: dict) -> str:
    """Salva uma memória persistente."""
    content = args.get("content", "").strip()
    if not content:
        return "❌ Parâmetro 'content' é obrigatório."

    mem_type = args.get("type", "observation")
    valid_types = ("fact", "decision", "preference", "observation")
    if mem_type not in valid_types:
        mem_type = "observation"

    tags = args.get("tags", "")
    now = datetime.now(timezone.utc).isoformat()

    try:
        conn = _get_db()
        conn.execute(
            "INSERT INTO memories (type, content, tags, created_at) VALUES (?, ?, ?, ?)",
            (mem_type, content, tags, now),
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        return f"✅ Memória salva ({mem_type}). Total: {count} memórias."
    except Exception as e:
        return f"❌ Erro ao salvar: {e}"


async def memory_search(args: dict) -> str:
    """Busca nas memórias persistentes."""
    query = args.get("query", "").strip()
    if not query:
        return "❌ Parâmetro 'query' é obrigatório."

    mem_type = args.get("type")
    limit = min(int(args.get("limit", 10)), 50)

    try:
        conn = _get_db()

        # Busca por LIKE em content e tags
        keywords = query.split()
        conditions = []
        params = []

        for kw in keywords:
            conditions.append("(content LIKE ? OR tags LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])

        where = " AND ".join(conditions)

        if mem_type:
            where += " AND type = ?"
            params.append(mem_type)

        sql = f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT ?"  # noqa: S608 — params are bind variables
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        conn.close()

        if not rows:
            return f"📭 Nenhuma memória encontrada para: {query}"

        parts = [f"🧠 {len(rows)} memória(s) encontrada(s):\n"]
        for row in rows:
            date = row["created_at"][:10]
            mem_type_icon = {
                "fact": "📌",
                "decision": "⚖️",
                "preference": "💜",
                "observation": "👁️",
            }.get(row["type"], "📝")

            tags_str = f" [{row['tags']}]" if row["tags"] else ""
            parts.append(f"{mem_type_icon} ({row['type']}) {date}{tags_str}\n  {row['content']}\n")

        return "\n".join(parts)
    except Exception as e:
        return f"❌ Erro ao buscar: {e}"


MEMORY_LIST_SPEC = {
    "type": "function",
    "function": {
        "name": "memory_list",
        "description": (
            "Lista as memórias persistentes mais recentes, sem necessidade de query. "
            "Use para revisar o que foi salvo, checar contexto de sessões anteriores, "
            "ou explorar memórias sem saber exatamente o que buscar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["fact", "decision", "preference", "observation"],
                    "description": "Filtrar por tipo (opcional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 20, máx: 50)",
                },
            },
            "required": [],
        },
    },
}


async def memory_list(args: dict) -> str:
    """Lista as memórias mais recentes."""
    mem_type = args.get("type")
    limit = min(int(args.get("limit", 20)), 50)

    try:
        conn = _get_db()

        if mem_type:
            rows = conn.execute(
                "SELECT * FROM memories WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (mem_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()

        if not rows:
            return "📭 Nenhuma memória salva ainda."

        type_icon = {
            "fact": "📌",
            "decision": "⚖️",
            "preference": "💜",
            "observation": "👁️",
        }

        parts = [f"🧠 {len(rows)} de {total} memória(s):\n"]
        for row in rows:
            date = row["created_at"][:10]
            icon = type_icon.get(row["type"], "📝")
            tags_str = f" [{row['tags']}]" if row["tags"] else ""
            parts.append(f"{icon} ({row['type']}) {date}{tags_str}\n  {row['content']}\n")

        return "\n".join(parts)
    except Exception as e:
        return f"❌ Erro ao listar: {e}"


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (MEMORY_SAVE_SPEC, "memory_save"),
    (MEMORY_SEARCH_SPEC, "memory_search"),
    (MEMORY_LIST_SPEC, "memory_list"),
]
