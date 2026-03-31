"""CRUD de memórias."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..db import get_db

router = APIRouter()


@router.get("/api/memories")
async def list_memories(
    type: str | None = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, ge=1, le=200),
):
    async with get_db() as db:
        if type:
            rows = await db.execute_fetchall(
                "SELECT id, type, content, tags, created_at FROM memories "
                "WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (type, limit),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT id, type, content, tags, created_at FROM memories "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        total_row = await db.execute_fetchall("SELECT COUNT(*) as n FROM memories")
        total = total_row[0]["n"] if total_row else 0
        return {"memories": [dict(r) for r in rows], "total": total}


@router.delete("/api/memories/{mem_id}")
async def delete_memory(mem_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        await db.commit()
    return {"ok": True}
