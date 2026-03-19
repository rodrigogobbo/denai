"""Memória persistente — save e search."""

import uuid
from datetime import datetime

from ..db import get_db

MEMORY_SAVE_SPEC = {
    "type": "function",
    "function": {
        "name": "memory_save",
        "description": "Salva uma informação na memória persistente para lembrar em futuras conversas.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Informação para lembrar"},
                "type": {
                    "type": "string",
                    "enum": ["fact", "decision", "preference", "observation"],
                },
                "tags": {"type": "string", "description": "Tags separadas por vírgula"},
            },
            "required": ["content"],
        },
    },
}

MEMORY_SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "memory_search",
        "description": "Busca informações na memória persistente.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Termo de busca"}},
            "required": ["query"],
        },
    },
}

TOOLS = [
    (MEMORY_SAVE_SPEC, "memory_save"),
    (MEMORY_SEARCH_SPEC, "memory_search"),
]


async def memory_save(args: dict) -> str:
    async with get_db() as db:
        mem_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO memories (id, type, content, tags, created_at) VALUES (?, ?, ?, ?, ?)",
            (mem_id, args.get("type", "observation"), args["content"], args.get("tags", ""), now),
        )
        await db.commit()
    return f"✅ Memória salva (id: {mem_id})"


async def memory_search(args: dict) -> str:
    async with get_db() as db:
        query = args["query"]
        rows = await db.execute_fetchall(
            "SELECT type, content, tags, created_at FROM memories "
            "WHERE content LIKE ? OR tags LIKE ? ORDER BY created_at DESC LIMIT 10",
            (f"%{query}%", f"%{query}%"),
        )
    if not rows:
        return "Nenhuma memória encontrada."
    return "\n".join(f"[{r[0]}] {r[1]} (tags: {r[2]}, {r[3][:10]})" for r in rows)
